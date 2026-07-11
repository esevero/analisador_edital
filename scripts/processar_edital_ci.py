"""
Processador de Editais — Versão CI (GitHub Actions)
Lê variáveis de ambiente e processa sem interação do terminal.
"""

import os
import sys
import re
import unicodedata
from pathlib import Path
from datetime import date

import pdfplumber
import yaml

# ─── Paths ───
ROOT = Path(__file__).parent.parent
EDITAIS_DIR = ROOT / "editais"
CONTENT_DIR = ROOT / "content" / "editais"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Variáveis de ambiente (vem do workflow) ───
PDF_FILE = os.environ.get("PDF_FILE", "")
CARGO = os.environ.get("CARGO", "")
SIGLA = os.environ.get("SIGLA", "")
ANO = os.environ.get("ANO", str(date.today().year))
OBSERVACOES = os.environ.get("OBSERVACOES", "")


def extrair_texto_pdf(caminho: Path) -> str:
    texto = ""
    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texto += t + "\n"
    return texto


def extrair_orgao(texto: str) -> dict:
    dados = {}
    # Nome
    m = re.search(
        r'((?:TRIBUNAL|ASSEMBLEIA|SECRETARIA|INSTITUTO|EMPRESA|FUNDAÇÃO|'
        r'UNIVERSIDADE|PREFEITURA|CÂMARA|MINISTÉRIO|GOVERNO)\s+'
        r'[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]+(?:DO|DA|DE|DOS|DAS)\s+'
        r'[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]+)', texto[:5000])
    if m:
        dados['orgao'] = m.group(1).strip()[:100]

    # Banca
    bancas = ['FCC', 'CEBRASPE', 'CESPE', 'FGV', 'IBFC', 'VUNESP', 'IDECAN',
              'INSTITUTO AVALIA', 'QUADRIX', 'AOCP', 'FUNCAB', 'CONSULPLAN']
    for b in bancas:
        if b in texto.upper()[:5000]:
            dados['banca'] = b.title() if b == 'INSTITUTO AVALIA' else b
            break

    return dados


def extrair_remuneracao(texto: str) -> dict:
    dados = {'gratificacoes': []}

    # Vencimento base
    padroes = [
        r'(?:vencimento|salário|subsídio|retribuição)\s*(?:base|básico|inicial)?\s*'
        r'(?:de|:|\s)*R\$\s*([\d.]+,\d{2})',
    ]
    for p in padroes:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            dados['vencimento_base'] = float(m.group(1).replace('.', '').replace(',', '.'))
            break

    # Gratificações
    grats = {
        'GAM': r'(?:GAM|Gratificação\s+de\s+Atividade\s+(?:do\s+)?Magistério)',
        'GDAP': r'(?:GDAP|Gratificação\s+de\s+Desempenho\s+(?:por\s+)?Atividade\s+de\s+Pesquisa)',
        'GDE': r'(?:GDE|Gratificação\s+de\s+Desempenho)',
        'ADFA': r'(?:ADFA|Adicional\s+de\s+Desempenho\s+(?:da\s+)?Fazend)',
        'GAEG': r'(?:GAEG|Gratificação\s+de\s+Atividade\s+de\s+Ensino)',
        'GDA': r'(?:GDA|Gratificação\s+de\s+Desempenho\s+de\s+Atividade)',
        'GAMS': r'(?:GAMS|Gratificação\s+de\s+Atividade\s+de\s+Magistério\s+Superior)',
        'GDPST': r'(?:GDPST|Gratificação\s+de\s+Desempenho.*?Previdência)',
        'GAE': r'(?:GAE|Gratificação\s+de\s+Atividade\s+Executiva)',
    }

    for sigla_g, padrao in grats.items():
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            pos = m.start()
            trecho = texto[pos:pos+800]
            grat = {'nome': sigla_g, 'valor_inicial': None, 'valor_maximo': None, 'percentual': '', 'base_calculo': '', 'observacao': ''}

            vals = re.findall(r'R\$\s*([\d.]+,\d{2})', trecho)
            if vals:
                grat['valor_inicial'] = float(vals[0].replace('.', '').replace(',', '.'))
                if len(vals) > 1:
                    grat['valor_maximo'] = float(vals[1].replace('.', '').replace(',', '.'))

            pcts = re.findall(r'(\d+(?:,\d+)?)\s*%', trecho)
            if pcts:
                grat['percentual'] = f"{pcts[0]}%" if len(pcts) == 1 else f"{pcts[0]}% a {pcts[-1]}%"

            dados['gratificacoes'].append(grat)

    # Remuneração total
    m = re.search(r'(?:remuneração|retribuição)\s*(?:total|inicial|bruta)\s*.*?R\$\s*([\d.]+,\d{2})', texto, re.IGNORECASE)
    if m:
        dados['remuneracao_total_inicial'] = float(m.group(1).replace('.', '').replace(',', '.'))

    return dados


def extrair_beneficios(texto: str) -> dict:
    dados = {}
    padroes = {
        'aux_alimentacao': r'(?:auxílio|vale)[\s\-]*(?:alimentação)\s*.*?R\$\s*([\d.]+,\d{2})',
        'aux_refeicao': r'(?:auxílio|vale)[\s\-]*(?:refeição)\s*.*?R\$\s*([\d.]+,\d{2})',
        'aux_saude': r'(?:auxílio|assistência)[\s\-]*(?:saúde|médic)\s*.*?R\$\s*([\d.]+,\d{2})',
        'aux_creche': r'(?:auxílio|assistência)[\s\-]*(?:creche|pré[\s\-]*escolar)\s*.*?R\$\s*([\d.]+,\d{2})',
    }
    for campo, padrao in padroes.items():
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            dados[campo] = float(m.group(1).replace('.', '').replace(',', '.'))
    return dados


def extrair_meta(texto: str) -> dict:
    dados = {}
    m = re.search(r'(\d+)\s*(?:horas?|h)\s*semana', texto, re.IGNORECASE)
    if m:
        dados['jornada_semanal'] = f"{m.group(1)} horas semanais"

    if 'CLT' in texto[:10000] or 'Consolidação das Leis' in texto[:10000]:
        dados['regime'] = 'CLT (Empresa Pública)'
    elif re.search(r'estatut[áa]rio|regime\s+jur[íi]dico\s+[úu]nico', texto[:10000], re.IGNORECASE):
        dados['regime'] = 'Estatutário'

    m = re.search(r'(\d+)\s*vaga', texto, re.IGNORECASE)
    if m:
        dados['vagas_total'] = int(m.group(1))

    return dados


def extrair_titulacao(texto: str) -> dict:
    dados = {}
    pats = {
        'especializacao_percentual': r'especialização.*?(\d+(?:,\d+)?)\s*%',
        'mestrado_percentual': r'mestrado.*?(\d+(?:,\d+)?)\s*%',
        'doutorado_percentual': r'doutorado.*?(\d+(?:,\d+)?)\s*%',
    }
    for campo, padrao in pats.items():
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            dados[campo] = float(m.group(1).replace(',', '.'))
    return dados


def gerar_slug(sigla: str, cargo: str, ano: str) -> str:
    texto = f"{sigla}-{ano}-{cargo}"
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'[^\w\s-]', '', texto.lower())
    texto = re.sub(r'[-\s]+', '-', texto).strip('-')
    return texto[:60]


CAMPOS_OBRIGATORIOS = [
    ('orgao', 'Nome completo do órgão'),
    ('sigla', 'Sigla do órgão'),
    ('banca', 'Banca organizadora'),
    ('regime', 'Regime jurídico'),
    ('jornada_semanal', 'Jornada semanal'),
    ('remuneracao.vencimento_base', 'Vencimento base inicial (R$)'),
    ('remuneracao.remuneracao_total_inicial', 'Remuneração total inicial (R$)'),
    ('beneficios.aux_alimentacao', 'Auxílio alimentação (R$/mês)'),
]


def get_nested(data, path):
    parts = path.split('.')
    val = data
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
    return val


def identificar_faltantes(dados):
    faltantes = []
    for campo, desc in CAMPOS_OBRIGATORIOS:
        val = get_nested(dados, campo)
        if val is None or val == '' or val == 0:
            faltantes.append({'campo': campo, 'descricao': desc})
    return faltantes


def main():
    pdf_path = EDITAIS_DIR / PDF_FILE
    if not pdf_path.exists():
        # Tentar com caminho direto
        pdf_path = ROOT / "editais" / PDF_FILE
        if not pdf_path.exists():
            print(f"❌ PDF não encontrado: {PDF_FILE}")
            print(f"   Procurado em: {EDITAIS_DIR / PDF_FILE}")
            sys.exit(1)

    print(f"📄 Processando: {pdf_path}")
    texto = extrair_texto_pdf(pdf_path)
    print(f"   ✅ {len(texto)} caracteres extraídos")

    # Extrair dados
    orgao_data = extrair_orgao(texto)
    remuneracao = extrair_remuneracao(texto)
    beneficios = extrair_beneficios(texto)
    meta = extrair_meta(texto)
    titulacao = extrair_titulacao(texto)

    # Montar dados
    sigla = SIGLA or orgao_data.get('sigla', '')
    slug = gerar_slug(sigla or 'concurso', CARGO, ANO)

    dados = {
        'id': slug,
        'status': 'parcial',
        'peso': 5,
        'data_processamento': date.today().strftime('%d/%m/%Y'),
        'edital_arquivo': PDF_FILE,
        'orgao': orgao_data.get('orgao', ''),
        'sigla': sigla,
        'esfera': '',
        'estado': '',
        'cidade': '',
        'banca': orgao_data.get('banca', ''),
        'edital_numero': '',
        'edital_ano': int(ANO) if ANO.isdigit() else date.today().year,
        'edital_link': '',
        'cargo': CARGO,
        'area': '',
        'escolaridade': 'Nível Superior',
        'formacao_exigida': '',
        'vagas_total': meta.get('vagas_total'),
        'regime': meta.get('regime', ''),
        'jornada_semanal': meta.get('jornada_semanal', ''),
        'local_trabalho': '',
        'remuneracao': remuneracao,
        'beneficios': beneficios,
        'carreira': {},
        'titulacao': titulacao,
        'trabalho': {},
        'localizacao': {},
        'notas': {},
        'fontes': [{'tipo': 'Oficial', 'descricao': f'Edital {PDF_FILE}', 'link': '', 'data': date.today().strftime('%d/%m/%Y')}],
        'dados_faltantes': [],
    }

    # Incorporar observações do usuário
    if OBSERVACOES:
        dados['observacoes_usuario'] = OBSERVACOES

    # Identificar faltantes
    faltantes = identificar_faltantes(dados)
    dados['dados_faltantes'] = faltantes
    if not faltantes:
        dados['status'] = 'completo'

    # Gerar MD
    front_matter = yaml.dump(dados, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    md_content = f"""---
{front_matter}---

## Análise Automática – {sigla or 'Concurso'} {ANO} – {CARGO}

**Processado automaticamente em {date.today().strftime('%d/%m/%Y')}**

### Dados Extraídos

| Campo | Valor |
|:------|------:|
| Órgão | {dados['orgao'] or '⚠️ Não encontrado'} |
| Cargo | {CARGO} |
| Banca | {dados['banca'] or '⚠️ Não encontrada'} |
| Regime | {dados['regime'] or '⚠️ Não encontrado'} |
| Venc. Base | {'R$ ' + f"{remuneracao.get('vencimento_base', 0):,.2f}" if remuneracao.get('vencimento_base') else '⚠️ Não encontrado'} |
| Remun. Total | {'R$ ' + f"{remuneracao.get('remuneracao_total_inicial', 0):,.2f}" if remuneracao.get('remuneracao_total_inicial') else '⚠️ Não encontrado'} |
| Aux. Alimentação | {'R$ ' + f"{beneficios.get('aux_alimentacao', 0):,.2f}" if beneficios.get('aux_alimentacao') else '⚠️ Não encontrado'} |
"""

    if remuneracao.get('gratificacoes'):
        md_content += "\n### Gratificações Encontradas\n\n"
        for g in remuneracao['gratificacoes']:
            vi = f"R$ {g['valor_inicial']:,.2f}" if g.get('valor_inicial') else '?'
            vm = f"R$ {g['valor_maximo']:,.2f}" if g.get('valor_maximo') else '?'
            md_content += f"- **{g['nome']}**: inicial {vi} | máximo {vm} | {g.get('percentual', '')}\n"

    if faltantes:
        md_content += "\n### ⚠️ Dados Pendentes\n\n"
        md_content += "Os seguintes campos não foram encontrados automaticamente:\n\n"
        for f in faltantes:
            md_content += f"- [ ] {f['descricao']} (`{f['campo']}`)\n"

    if OBSERVACOES:
        md_content += f"\n### Observações do Usuário\n\n{OBSERVACOES}\n"

    # Salvar
    output_path = CONTENT_DIR / f"{slug}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"\n✅ Gerado: {output_path}")
    print(f"   Status: {dados['status']}")
    print(f"   Dados faltantes: {len(faltantes)}")
    if remuneracao.get('gratificacoes'):
        for g in remuneracao['gratificacoes']:
            print(f"   📌 Gratificação encontrada: {g['nome']}")


if __name__ == '__main__':
    main()
