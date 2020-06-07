import os
import html
import subprocess
import logging
import tempfile

from typing import Dict, List, Union
from pathlib import Path

import encoding
from exceptions import DoesNotExist


logger = logging.getLogger(__name__)

PRESERVECIRC = "[PRESERVECIRC]"


def read_file(filename, encode="utf-8"):
    try:
        with open(filename, "r", encoding=encode) as fp:
            content = fp.read()
    except (FileNotFoundError, OSError) as e:
        raise e
    else:
        return content


def remove_break_lines_characters(content):
    content = content or ""
    return " ".join(content.split())


def format_value(content):
    """Formata o valor de um subcampo ou campo sem subcampo"""
    try:
        content += ""
    except TypeError:
        content = ", ".join(content)
    return remove_break_lines_characters(content).strip().replace("^", PRESERVECIRC)


class IDFile:

    MAX_DIGITS_QTD = 6
    VALID_ID_RANGE = range(1, 10 ** MAX_DIGITS_QTD)

    def __init__(self, content_formatter=None):
        self.content_formatter = content_formatter

    def _format_file(self, records):
        r = []
        index = 0
        for item in records:
            index += 1
            r.append(self._format_id(index) + self._format_record(item))
        return "".join(r)

    def _format_id(self, index):
        """
        Cria o ID do registro
        """
        if index in self.VALID_ID_RANGE:
            return "!ID {}\n".format(str(index).zfill(self.MAX_DIGITS_QTD))
        raise IndexError("IDFile._format_id: {} is out of range".format(index))

    def _format_record(self, record):
        """
        Formata o registro
        """
        if record:
            items = []
            for tag_i in sorted([int(s) for s in record.keys()]):
                tag = str(tag_i)
                items.extend(self._tag_data(tag, record[tag]))
            result = "".join(items)
            if self.content_formatter:
                result = self.content_formatter(result)
            return result
        return ""

    def _tag_data(self, tag, data):
        """
        Cria os campos com respectivos conteúdos
        """
        if not data:
            return []
        occs = []
        if not isinstance(data, list):
            data = [data]
        for item in data:
            occs.append(self._tag_occ(tag, item))
        return occs

    def _tag_occ(self, tag, data):
        """
        Cria cada ocorrência de um dado campo
        """
        if not data:
            return ""
        try:
            data = {"_": data + ""}
        except TypeError:
            if not isinstance(data, dict):
                raise TypeError("IDFile.tag_occ expects dict or str")
        return self._tag_content(tag, self._format_subfields(data))

    def _format_subfield(self, subf, subf_value):
        if subf_value and subf in "abcdefghijklmnopqrstuvwxyz123456789":
            return "^" + subf + format_value(subf_value)
        return ""

    def _format_subfields(self, subf_and_value_list):
        first = format_value(subf_and_value_list.get("_") or "")
        values = [self._format_subfield(k, v) for k, v in subf_and_value_list.items()]
        value = "".join(sorted(values))
        return first + value

    def _tag_content(self, tag, value):
        if not 0 < int(tag) <= 999:
            raise ValueError("IDFile.tag_content expects tag <= 999")
        if not value:
            return ""
        return "!v{}!{}\n".format(tag.zfill(3), value)

    def _get_field_data(self, field_content):
        subfields = field_content.split("^")
        subfields = [c.replace(PRESERVECIRC, "^") for c in subfields]

        if len(subfields) == 1:
            # sem subcampos
            return subfields[0]
        # com subcampos
        d = {}
        if subfields[0]:
            d.update({"_": subfields[0]})
        for subf in subfields[1:]:
            d.update({subf[0]: subf[1:]})
        return d

    def _get_record_data(self, record):
        fields = record.split("\n!v")[1:]
        data: Dict[str, list] = {}
        for field in fields:
            field_tag = str(int(field[:3]))
            field_content = field[4:].strip()
            field_data = self._get_field_data(field_content)
            data[field_tag] = data.get(field_tag, [])
            data[field_tag].append(field_data)

        for tag, tag_content in data.items():
            if len(tag_content) == 1:
                data[tag] = tag_content[0]
        return data

    def read(self, filename):
        rec_list = []
        iso_content = read_file(filename, "iso-8859-1")
        utf8_content = encoding.decode(iso_content)
        utf8_content = html.unescape(utf8_content)
        utf8_content = utf8_content.replace("\\^", PRESERVECIRC)

        records = utf8_content.split("!ID ")
        for record in records[1:]:
            data = self._get_record_data(record)
            rec_list.append(data)
        return rec_list

    def write(self, filename, records):
        path = os.path.dirname(filename)
        if not os.path.isdir(path):
            os.makedirs(path)
        content = self._format_file(records)
        content = html.unescape(content)

        content = content.replace(PRESERVECIRC, "\\^")

        # converterá a entidades, os caracteres utf-8 que não tem
        # correspondencia em iso-8859-1
        content = encoding.encode(content, "iso-8859-1")
        content = encoding.decode(content, "iso-8859-1")

        try:
            # write_file(filename, content, "iso-8859-1")
            with open(filename, "w", encoding="iso-8859-1") as fp:
                fp.write(content)
        except (UnicodeError, IOError, OSError) as e:
            print("Nao foi possivel escrever o arquivo {}: {}".format(filename, str(e)))


class CISIS:
    """Interface with C ISIS utilities.
    
    Whit this classe you should be capable to search into ISIS databas,
    write registers and update as well.

    This class run commands into bash to call C ISIS"""

    def __init__(self, cisis_path: str):
        self.cisis_path: Path = Path(cisis_path)

        if not self.cisis_path.exists():
            raise DoesNotExist(
                "Could not initialize the '%s' class. The path '%s' does not exist."
                % (self.__class__.__name__, self.cisis_path)
            ) from None

    def run_cmd(self, cmd_name: str, *args):
        """At the final rood this method calls an subprocess to run the ISIS
        tool binary"""
        cmd = "{cmd_name}  {arguments}".format(
            cmd_name=os.path.join(self.cisis_path.name, cmd_name),
            arguments=" ".join(args),
        )
        logger.debug("Running:\n {}".format(cmd))
        return subprocess.getoutput(cmd)

    def is_available(self):
        output = self.run_cmd("mx", "what")
        return output and output.startswith("CISIS")

    def crunchmf(self, mst_filename, wmst_filename):
        self.run_cmd("crunchmf", mst_filename, wmst_filename)

    def id2i(self, id_filename, mst_filename):
        # Cria base MST
        self.run_cmd("id2i", id_filename, "create=" + mst_filename)

    def append(self, src, dest):
        self.run_cmd("mx", src, "append={}".format(dest), "now -all")

    def create(self, src, dest):
        self.run_cmd("mx", src, "create={}".format(dest), "now -all")

    def append_id_to_master(self, id_filename, mst_filename, reset):
        if reset:
            self.id2i(id_filename, mst_filename)
        else:
            temp = id_filename.replace(".id", "")
            self.id2i(id_filename, temp)
            self.append(temp, mst_filename)
            self.delete(temp)

    def delete(self, db_file_path: str) -> None:
        for extension in [".mst", ".xrf"]:
            path = Path(f"{db_file_path}{extension}")
            if not path.exists():
                continue
            path.unlink()
            logger.debug("Removed file '%s'.", path.name)

    def i2id(self, mst_filename, id_filename):
        self.run_cmd("i2id", mst_filename, ">", id_filename)

    def mst2iso(self, mst_filename, iso_filename):
        self.run_cmd("mx", mst_filename, "iso={}".format(iso_filename), "now -all")

    def iso2mst(self, iso_filename, mst_filename):
        self.run_cmd(
            "mx",
            "iso={}".format(iso_filename),
            "create={}".format(mst_filename),
            "now -all",
        )

    def new(self, mst_filename):
        self.run_cmd("mx", "null count=0", "create={}".format(mst_filename), "now -all")

    def search(self, mst_filename: str, expression: str, result_filename: str) -> str:
        # Realiza uma query na base completa e exporta o resultado da query
        # em um arquivo a parte. Na prática fatia o banco em um sub banco
        self.delete(result_filename)
        return self.run_cmd(
            "mx",
            "btell=0",
            mst_filename,
            '"bool={}"'.format(expression),
            "lw=999",
            "append={}".format(result_filename),
            "now -all",
        )

    def generate_indexes(self, mst_filename, fst_filename, inverted_filename):
        self.run_cmd(
            "mx",
            mst_filename,
            "fst=@{}".format(fst_filename),
            "fullinv={}".format(inverted_filename),
        )

    def is_readable(self, mst_filename):
        if os.path.isfile(mst_filename + ".mst"):
            result = self.run_cmd("mx", mst_filename, "+control now")
            return "dbxopen" not in result or "nxtmfn" in result
        return False


class UCISIS:
    """Still don't know what U means"""

    def __init__(self, cisis1030_path: str, cisis1660_path: str):
        self.idfile = IDFile()
        self.cisis1030: CISIS = CISIS(cisis1030_path)
        self.cisis1660: CISIS = CISIS(cisis1660_path)

    def is_available(self) -> bool:
        return self.cisis1660.is_available() or self.cisis1030.is_available()

    def cisis(self, mst_filename) -> CISIS:
        if not os.path.isfile("%s.mst" % mst_filename):
            logger.debug("Could not find MST file '%s'" % mst_filename)
            return self.cisis1030

        for CISIS in [self.cisis1030, self.cisis1660]:
            if CISIS.is_readable(mst_filename):
                return CISIS

        raise Exception("Database is locked cannot read")

    def version(self, mst_filename) -> str:
        if self.cisis1030.is_readable(mst_filename):
            return "1030"
        elif self.cisis1660.is_readable(mst_filename):
            return "1660"

        raise Exception("Could not find database version")

    # dead code?
    # def convert1660to1030(self, mst_filename):
    #     if os.path.isfile(mst_filename + ".mst"):
    #         temp_file = NamedTemporaryFile(delete=False)
    #         temp_file.close()
    #         self.cisis1660.mst2iso(mst_filename, temp_file.name)
    #         self.cisis1030.iso2mst(temp_file.name, mst_filename)
    #         fs_utils.delete_file_or_folder(temp_file.name)

    def crunchmf(self, mst_filename, wmst_filename):
        self.cisis(mst_filename).crunchmf(mst_filename, wmst_filename)

    def id2i(self, id_filename, mst_filename):
        self.cisis(mst_filename).id2i(id_filename, mst_filename)

    def append(self, src, dest):
        self.cisis(src).append(src, dest)

    def create(self, src, dest):
        self.cisis(src).create(src, dest)

    def append_id_to_master(self, id_filename, mst_filename, reset):
        self.cisis(mst_filename).append_id_to_master(id_filename, mst_filename, reset)

    def i2id(self, mst_filename, id_filename):
        self.cisis(mst_filename).i2id(mst_filename, id_filename)

    def mst2iso(self, mst_filename, iso_filename):
        self.cisis(mst_filename).mst2iso(mst_filename, iso_filename)

    def iso2mst(self, iso_filename, mst_filename):
        self.cisis(mst_filename).iso2mst(iso_filename, mst_filename)

    def new(self, mst_filename):
        self.cisis1030.new(mst_filename)

    def search(self, mst_filename, expression, result_filename):
        self.cisis(mst_filename).search(mst_filename, expression, result_filename)

    def generate_indexes(self, mst_filename, fst_filename, inverted_filename):
        self.cisis(mst_filename).generate_indexes(
            mst_filename, fst_filename, inverted_filename
        )

    def update_indexes(self, db_filename, fst_filename):
        if fst_filename is not None:
            self.generate_indexes(db_filename, fst_filename, db_filename)

    def id_file_to_db(self, id_filename, db_filename, fst_filename=None):
        self.id2i(id_filename, db_filename)
        self.update_indexes(db_filename, fst_filename)

    def append_id_file_to_db(self, id_filename, db_filename, fst_filename=None):
        self.append_id_to_master(id_filename, db_filename, False)
        self.update_indexes(db_filename, fst_filename)

    def get_records(
        self, db_filename, expr: str = None
    ) -> List[Dict[str, Union[str, list]]]:
        """Retorna uma lista de registros a partir da leitura de uma base ID"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_name = os.path.join(
                temporary_directory, os.path.basename(db_filename)
            )

            if expr is None or len(expr) == 0:
                database_name = db_filename
            else:
                self.search(db_filename, expr, database_name)

            if not os.path.isfile("%s.mst" % database_name):
                return []

            # Cria ID file a partir da base MST
            id_filename = "%s.id" % database_name
            self.i2id(database_name, id_filename)
            return self.idfile.read(id_filename)  # Ler arquivo ID

    def create_id_file(self, id_filename, records, content_formatter=None):
        if content_formatter:
            IDFile(content_formatter).write(id_filename, records)
        else:
            self.idfile.write(id_filename, records)


__all__ = ["UCISIS"]
