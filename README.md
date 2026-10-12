# Encurtador de Links

Projeto de estudo: um encurtador de URLs em Flask + SQLite, com redirecionamento, alias personalizado e contagem de cliques.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000

## Testes

```bash
pytest
```

## API

| Método | Rota                | Descrição                                           |
|--------|---------------------|-----------------------------------------------------|
| POST   | `/api/shorten`      | Corpo: `{"url": "...", "alias": "opcional"}`        |
| GET    | `/<codigo>`         | Redireciona (302) para a URL original               |
| GET    | `/api/stats/<codigo>` | Retorna URL, cliques e data de criação            |

Exemplo:

```bash
curl -X POST localhost:5000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://exemplo.com/um/caminho/longo"}'
```

## Decisões de design

- **Código em base62 a partir do ID do banco.** Cada link recebe um ID autoincrementado, somado a um offset (100.000) e convertido para base62. Não há colisões entre códigos gerados e não precisa de checagem aleatória. Se um alias personalizado ocupar um código, o gerador avança para o próximo.
- **302 em vez de 301.** O 301 é cacheado pelo navegador, então os cliques seguintes nem chegariam ao servidor e a contagem ficaria errada.
- **Validação de URL.** Só aceita `http` e `https` (bloqueia `javascript:` e similares) e limita o tamanho a 2048 caracteres.
- **Aliases.** 3 a 32 caracteres (letras, números, `-`, `_`), com nomes reservados para não conflitar com rotas.

## Limitações atuais (e próximos passos)

Pontos que dariam bons incrementos para o portfólio:

- Rate limiting (ex.: Flask-Limiter) para evitar abuso.
- Expiração de links.
- Cache dos redirects (Redis) e contagem de cliques assíncrona.
- Analytics por clique (data, navegador, país) em uma tabela separada.
- Contas de usuário e painel com os links de cada pessoa.
- Checagem de URLs contra listas de phishing/malware.
- Trocar SQLite por PostgreSQL e rodar atrás de gunicorn + Docker.
- IDs sequenciais deixam os links previsíveis; para evitar enumeração, dá para embaralhar o ID antes de codificar (ex.: biblioteca Sqids).
