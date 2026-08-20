# 🛍️ Bot da Loja para Discord

Um bot em Python (discord.py) com **moderação**, **comandos customizados**,
**boas-vindas + auto-cargos** e um **painel de loja minimalista** onde você
cadastra e salva todos os produtos da sua loja. Tudo fica guardado num banco
de dados local (`bot.db`), então nada se perde quando o bot reinicia.

---

## 1. Criar o bot no Discord (só você consegue fazer isto — precisa da sua conta)

1. Acesse **https://discord.com/developers/applications** e faça login.
2. Clique em **New Application**, dê um nome (ex.: "Loja") e confirme.
3. No menu à esquerda, vá em **Bot**.
4. Em **Privileged Gateway Intents**, ligue a opção **SERVER MEMBERS INTENT**
   (é o que permite as boas-vindas e o auto-cargo funcionarem).
5. Clique em **Reset Token** → **Copy**. Guarde esse token com cuidado —
   ele é a senha do seu bot, nunca compartilhe.

> ⚠️ Se o token vazar, volte aqui e clique em **Reset Token** de novo para
> invalidar o antigo.

## 2. Convidar o bot para o seu servidor

1. Ainda no portal, vá em **OAuth2 → URL Generator**.
2. Em **Scopes**, marque: `bot` e `applications.commands`.
3. Em **Bot Permissions**, marque pelo menos:
   *Manage Roles, Kick Members, Ban Members, Manage Messages, Moderate Members,
   Send Messages, Embed Links, Read Message History*.
4. Copie a URL que aparece embaixo, cole no navegador, escolha o seu servidor
   e clique em **Autorizar**.

> Importante: no seu servidor, arraste o **cargo do bot para cima** dos cargos
> que ele precisa gerenciar (ex.: o cargo de auto-role). O bot só consegue
> mexer em cargos/membros que estejam **abaixo** dele.

## 3. Rodar o bot

Precisa ter **Python 3.10+** instalado.

```bash
# dentro da pasta do projeto
pip install -r requirements.txt

# copie o modelo de configuração e edite
cp .env.example .env      # no Windows: copy .env.example .env
```

Abra o arquivo `.env` e cole o seu token em `DISCORD_TOKEN=`.
(Opcional) coloque o ID do seu servidor em `GUILD_ID=` para os comandos de
barra aparecerem na hora.

```bash
python main.py
```

Quando aparecer `Conectado como ...` no terminal, está no ar. ✅

---

## 4. Comandos disponíveis

### Loja
| Comando | O que faz |
|---|---|
| `/loja config` | Define nome, moeda e cor da loja |
| `/loja add` | Cadastra um produto (nome, preço, descrição, estoque, imagem) |
| `/loja edit` | Edita um produto pelo ID |
| `/loja remove` | Remove um produto pelo ID |
| `/loja ver` | Abre o catálogo navegável (público) |

### Moderação
| Comando | O que faz |
|---|---|
| `/ban` `/kick` | Bane ou expulsa um membro |
| `/timeout` | Silencia por X minutos |
| `/clear` | Apaga mensagens do canal |
| `/warn` `/warnings` | Adverte e consulta advertências |

### Boas-vindas
| Comando | O que faz |
|---|---|
| `/config-boasvindas` | Canal + mensagem (variáveis: `{mention}`, `{user}`, `{server}`, `{count}`) |
| `/config-autorole` | Cargo dado automaticamente a quem entra |

### Comandos customizados
| Comando | O que faz |
|---|---|
| `/cc add` | Cria uma resposta rápida |
| `/cc run` | Dispara a resposta |
| `/cc list` `/cc remove` | Lista / remove |

---

## Estrutura do projeto

```
discord-bot/
├── main.py            # inicia o bot
├── database.py        # banco SQLite (config, loja, comandos, warns)
├── requirements.txt
├── .env.example       # modelo de configuração
├── bot.db             # criado automaticamente na 1ª execução
└── cogs/
    ├── moderation.py
    ├── welcome.py
    ├── custom_commands.py
    └── store.py
```

## Dicas de hospedagem (deixar o bot ligado 24h)

O bot precisa de um computador ligado o tempo todo. Opções comuns e baratas:
**Railway**, **Render**, **Fly.io** ou uma **VPS**. Se quiser, me chame que eu
te ajudo a preparar o deploy em qualquer uma delas.
