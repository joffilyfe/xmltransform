# Programa

Entrada:
- `--config config.ini`
- `--convert`
- `--reports x y z`
- `--update-website`
- `--export-spf`
- `--export-ftp`
- `--export-pubmed`


### Atual
O programa inicia:
1) Carrega configurações
2) O programa carrega a lista de periódicos a partir de um arquivo CSV
2.1) Uma lista de periódicos é instanciada a partir desse CSV
3) Carrega base Issue

### Pensamento
- Pacote carregado
- Artigo transformado em objeto python
- As validações to packtools são executadas
- Validações (Validation) são executadas [lista]
- O resultado das validações é observável por uma estrutura de chave-valor
- O artigo é transformado em base mst / id