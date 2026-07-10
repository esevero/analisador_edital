# 📋 Analisador de Editais de Concursos

Plataforma genérica para análise de editais de concursos públicos. Faz upload de qualquer edital PDF, extrai dados automaticamente, salva em Markdown no repositório e gera comparativos visuais com gráficos.

## Como Funciona

```
PDF do Edital → Script Python → Extrai dados → Gera .md → Git push → Site atualiza
                     ↓
         Dados não encontrados?
                     ↓
         Pergunta ao usuário via terminal
```

## Uso Rápido

### 1. Instalar dependências

```bash
# Python (processador de PDF)
pip install -r scripts/requirements.txt

# Node.js (site)
npm install
```

### 2. Processar um edital

```bash
# Coloque o PDF na pasta editais/
python scripts/processar_edital.py editais/meu-edital.pdf

# O script vai:
# 1. Extrair texto do PDF
# 2. Listar cargos encontrados
# 3. Perguntar qual cargo analisar
# 4. Extrair: remuneração, gratificações, benefícios, carreira, titulação
# 5. Gerar arquivo .md em content/editais/
# 6. Listar dados que não encontrou
# 7. Perguntar se quer preencher os faltantes
```

### 3. Publicar

```bash
git add .
git commit -m "Adiciona edital XPTO-2026"
git push
# GitHub Pages rebuilda automaticamente
```

### 4. Desenvolvimento local

```bash
npm run dev
# Abre http://localhost:4321
```

## Estrutura do Projeto

```
analisador-editais/
├── content/editais/         ← Editais processados (.md com front-matter YAML)
│   ├── _schema.md           ← Template/schema de referência
│   ├── tjce-2026-*.md       ← Exemplo: TJCE
│   └── ipece-2023-*.md      ← Exemplo: IPECE
├── scripts/
│   ├── processar_edital.py  ← Script de processamento de PDF
│   └── requirements.txt     ← Dependências Python
├── src/
│   ├── pages/               ← Páginas do site Astro
│   ├── layouts/             ← Layout base
│   ├── components/          ← Componentes reutilizáveis
│   └── lib/                 ← Utilitários
├── public/assets/css/       ← Estilos
├── .github/workflows/       ← Deploy automático GitHub Pages
├── astro.config.mjs         ← Config Astro
└── package.json
```

## O que é extraído automaticamente

| Dado | Método |
|------|--------|
| Nome do órgão | Regex em maiúsculas no início |
| Banca | Match contra lista conhecida (FCC, CEBRASPE, FGV...) |
| Cargos | Padrões "Analista...", "Técnico...", "Auditor..." |
| Vencimento base | Regex R$ + contexto "vencimento/salário base" |
| Gratificações | Match de siglas (GAM, GDAP, GDE, ADFA, GAEG, GDA) |
| Auxílios | Regex "auxílio alimentação/saúde/creche" + valor |
| Vagas | Número + "vaga(s)" |
| Regime | CLT vs Estatutário |
| Titulação | Percentuais próximos a "especialização/mestrado/doutorado" |

## Dados Faltantes

Quando o script não encontra um campo obrigatório:

1. **No terminal**: pergunta se quer preencher na hora
2. **No arquivo .md**: marca na lista `dados_faltantes`
3. **No site**: exibe formulário visual com os campos pendentes

## Páginas do Site

- **Início** — Dashboard com stats e editais recentes
- **Editais** — Lista completa com filtros
- **Comparativo** — Tabela + gráfico de barras comparando remuneração
- **Ranking** — Classificação ponderada + gráfico radar
- **Adicionar** — Instruções de como adicionar novos editais

## Tecnologias

- **Astro** — Site estático com suporte a Markdown/MDX
- **Chart.js** — Gráficos interativos
- **Python + pdfplumber** — Extração de texto de PDF
- **GitHub Pages** — Hospedagem gratuita
- **GitHub Actions** — Deploy automático

## Configuração GitHub Pages

1. Crie repositório no GitHub
2. Vá em Settings → Pages → Source: GitHub Actions
3. Edite `astro.config.mjs` com seu usuário/repo
4. Push para `main` → deploy automático

## Licença

Uso pessoal para apoio à decisão de carreira.
