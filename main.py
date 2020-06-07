import abc
import sys
import logging
import enum

from pathlib import Path
from collections import namedtuple
from typing import (
    List,
    Dict,
    Union,
    Sequence,
    Mapping,
    TypeVar,
    Tuple,
    Type,
    Optional,
    NamedTuple,
)

from isisinterface import UCISIS

logging.basicConfig(format=u"%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s",)
logger = logging.getLogger()
logger.setLevel("INFO")


Record = Dict[str, Union[str, list]]
Records = List[Record]


class ValidationSeverityError(enum.Enum):
    """Enum with severity of errors"""
    Warning = enum.auto()
    Blocking = enum.auto()
    Fatal = enum.auto()


class ValidationDict(NamedTuple):
    failed: bool
    reason: str
    severity: ValidationSeverityError


ValidationResult = Union[ValidationDict, None]


class ISISDatabase(abc.ABC):
    @abc.abstractmethod
    def search(self, **kwargs) -> Records:
        """Search for records into ISIS Database.
        
        It uses the UCISIS interfaces to access MX power"""
        raise NotImplementedError


class IssueDatabase(ISISDatabase):
    def __init__(self, file: Path, fst: Path, engine: UCISIS):
        self.file = file
        self.fst = fst
        self.engine = engine

    def search(self, **kwargs) -> Records:
        """Search for issues into ISIS"""
        query = " OR ".join([value for key, value in kwargs.items()])
        return self.engine.get_records(self.file, query)


class Validation(abc.ABC):
    """Abstract validation template"""

    @abc.abstractmethod
    def __init__(self, severity: ValidationSeverityError):
        self.severity: ValidationSeverityError = severity

    @abc.abstractmethod
    def check(self, **kwargs) -> ValidationResult:
        raise NotImplementedError


class ArticleTitleValidation(Validation):
    """Checks if the article title is good according
    SciELO specification"""

    def __init__(self):
        super().__init__(ValidationSeverityError.Blocking)

    def check(self, **kwargs) -> ValidationResult:
        title: str = kwargs.get("title", "")

        if len(title.strip()) == 0:
            return ValidationDict(
                failed=True, reason="Title cannot be blank", severity=self.severity
            )

        return None


class ArticleAuthorsValidation(Validation):
    """Checks if article have authors"""

    def __init__(self):
        super().__init__(ValidationSeverityError.Blocking)

    def check(self, **kwargs) -> ValidationResult:
        authors: str = kwargs.get("article", {}).get("authors", [])

        if len(authors) == 0:
            return ValidationDict(
                failed=True,
                reason="The article shoud have at least one author",
                severity=self.severity,
            )

        return None


if __name__ == "__main__":
    Base = namedtuple("Base", ["name", "mst", "xrf"])

    # engine: UCISIS = UCISIS(
    #     "/home/scielo/.bin/cisis", "/home/scielo/.bin/cisis",
    # )

    # bases = {
    #     "title": Base(
    #         "/home/scielo/.testes/workspace/title-copy",
    #         "/home/scielo/.testes/workspace/title-copy.mst",
    #         "/home/scielo/.testes/workspace/title-copy.xrf",
    #     ),
    #     "issue": Base(
    #         "/home/scielo/.testes/workspace/issue-copy",
    #         "/home/scielo/.testes/workspace/issue-copy.mst",
    #         "/home/scielo/.testes/workspace/issue-copy.xrf",
    #     ),
    # }

    # for name, BASE in bases.items():
    #     db = IssueDatabase(BASE.name, Path("/tmp/fst"), engine)
    #     # records: Records = db.search(id="1516-44462020nahead")
    #     records: Records = db.search(title="Brazilian Journal of Psychiatry")
    #     print(records)

    # Pacote carregado
    # Artigo transformado em objeto python
    # As validações to packtools são executadas
    # Validações (Validation) são executadas [lista]
    # O resultado das validações é observável por uma estrutura de chave-valor
    # O artigo é transformado em base mst / id

    article_validations: List[Validation] = [
        ArticleTitleValidation(),
        ArticleAuthorsValidation(),
    ]

    validations_results: List[ValidationResult] = []

    for validation in article_validations:
        check = validation.check(
            article={"authors": ["First author", "Second author"]},
        )
        validations_results.append(check)

    # inicia processos de report
    for result in validations_results:
        if result is None:
            continue

        if result.severity == ValidationSeverityError.Blocking:
            logger.error("Could not convert this article, reason '%s'.", result.reason)
