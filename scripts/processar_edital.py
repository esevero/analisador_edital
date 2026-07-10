"""
═══════════════════════════════════════════════════════════════════════════
PROCESSADOR DE EDITAIS DE CONCURSO
═══════════════════════════════════════════════════════════════════════════

Uso:
  python scripts/processar_edital.py <arquivo.pdf> [--cargo "Nome do Cargo"]

O que faz:
  1. Extrai texto do PDF (pdfplumber)
  2. Identifica cargos disponíveis
  3. Pergunta qual cargo analisar (se não informado)
  4. Extrai automaticamente: remuneração, gratificações, benefícios, carreira, etc.
  5. Gera arquivo .md em content/editais/ com front-matter YAML
  6. Lista campos que não conseguiu extrair (dados_faltantes)
  7. Abre formulário interativo no terminal para completar dados faltantes

Dependências:
  pip install pdfplumber pyyaml rich questionary
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import date

try:
    import pdfplumber
except ImportError:
    print("❌ Instale: pip install pdfplumber")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("❌ Instale: pip install pyyaml")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    console = None
    print("⚠️  Instale 'rich' para interface bonita: pip install rich")

try:
    import questionary
except ImportError:
    questionary = None


# ─────────────────────────── CONFIGURAÇÃO ────────────────────────────────
CONTENT_DIR = Path(__file__).parent.parent / "content" / "editais"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────── EXTRAÇÃO DE TEXTO ───────────────────────────

def extrair_texto_pdf(caminho_pdf: str) -> str:
    """Extrai todo o texto de um PDF usando pdfplumber."""
    texto = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texto += page_text + "\n"
    return texto


# ─────────────────────────── IDENTIFICAÇÃO DE CARGOS ─────────────────────

def encontrar_cargos(texto: str) -> list:
    """Identifica cargos mencionados no edital."""
    padroes = [
        r'(?:cargo|função|emprego)\s*(?:de|:)?\s*([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][a-záéíóúâêîôûãõç\s\-–]+(?:de\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][a-záéíóúâêîôûãõç\s]+)?)',
        r'(?:CARGO|FUNÇÃO)\s*\d*\s*[:\-–]?\s*([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s\-–]+)',
        r'(Analista\s+[A-Za-záéíóúâêîôûãõç\s\-–]+)',
        r'(Técnico\s+[A-Za-záéíóúâêîôûãõç\s\-–]+)',
        r'(Auditor\s+[A-Za-záéíóúâêîôûãõç\s\-–]+)',
    ]
    cargos = set()
    for padrao in padroes:
        matches = re.findall(padrao, texto)
        for m in matches:
            cargo = m.strip()
            if len(cargo) > 5 and len(cargo) < 80:
                cargos.add(cargo)
    return sorted(cargos)


# ─────────────────────────── EXTRAÇÃO DE DADOS ───────────────────────────

def extrair_orgao(texto: str) -> dict:
    """Extrai informações do órgão."""
    dados = {}

    # Nome do órgão
    m = re.search(r'(?:TRIBUNAL|ASSEMBLEIA|SECRETARIA|INSTITUTO|EMPRESA|FUNDAÇÃO|UNIVERSIDADE|PREFEITURA|CÂMARA|MINISTÉRIO)\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]+(?:DO|DA|DE|DOS|DAS)\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]+', texto[:3000])
    if m:
        dados['orgao'] = m.group(0).strip()

    # Sigla
    m = re.search(r'\b([A-Z]{2,10}(?:/[A-Z]{2})?)\b', texto[:1000])
    if m:
        sigla = m.group(1)
        if len(sigla) >= 3:
            dados['sigla'] = sigla

    # Banca
    bancas_conhecidas = ['FCC', 'CEBRASPE', 'CESPE', 'FGV', 'IBFC', 'VUNESP', 'IDECAN',
                         'Instituto Avalia', 'QUADRIX', 'AOCP', 'FUNCAB', 'CONSULPLAN']
    for banca in bancas_conhecidas:
        if banca.upper() in texto.upper()[:5000]:
            dados['banca'] = banca
            break

    return dados


def extrair_remuneracao(texto: str, cargo: str) -> dict:
    """Extrai valores de remuneração."""
    dados = {'gratificacoes': []}

    # Buscar valores monetários próximos ao cargo
    # Padrão: R$ X.XXX,XX
    valores = re.findall(r'R\$\s*([\d.]+,\d{2})', texto)
    valores_float = []
    for v in valores:
        try:
            val = float(v.replace('.', '').replace(',', '.'))
            if val > 1000 and val < 100000:
                valores_float.append(val)
        except:
            pass

    # Vencimento base - procurar padrões
    padroes_vencimento = [
        r'(?:vencimento|salário|subsídio|remuneração)\s*(?:base|básico|inicial)?\s*(?:de|:)?\s*R\$\s*([\d.]+,\d{2})',
        r'(?:vencimento|salário)\s*(?:base)?\s*.*?R\$\s*([\d.]+,\d{2})',
    ]
    for padrao in padroes_vencimento:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            val = float(m.group(1).replace('.', '').replace(',', '.'))
            if val > 1000:
                dados['vencimento_base'] = val
                break

    # Gratificações conhecidas
    grats_padroes = {
        'GAM': r'(?:GAM|Gratificação\s+de\s+Atividade\s+(?:do\s+)?Magistério)',
        'GDAP': r'(?:GDAP|Gratificação\s+de\s+Desempenho\s+(?:por\s+)?Atividade\s+de\s+Pesquisa)',
        'GDE': r'(?:GDE|Gratificação\s+de\s+Desempenho)',
        'ADFA': r'(?:ADFA|Adicional\s+de\s+Desempenho\s+Fazendário)',
        'GAEG': r'(?:GAEG|Gratificação\s+de\s+Atividade\s+de\s+Ensino)',
        'GDA': r'(?:GDA|Gratificação\s+de\s+Desempenho\s+de\s+Atividade)',
    }

    for sigla_grat, padrao in grats_padroes.items():
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            # Procurar valor próximo
            pos = m.start()
            trecho = texto[pos:pos+500]
            vals = re.findall(r'R\$\s*([\d.]+,\d{2})', trecho)
            grat = {'nome': sigla_grat, 'valor_inicial': None, 'valor_maximo': None, 'percentual': ''}

            if vals:
                grat['valor_inicial'] = float(vals[0].replace('.', '').replace(',', '.'))
                if len(vals) > 1:
                    grat['valor_maximo'] = float(vals[1].replace('.', '').replace(',', '.'))

            # Percentual
            pcts = re.findall(r'(\d+(?:,\d+)?)\s*%', trecho)
            if pcts:
                grat['percentual'] = f"{pcts[0]}%"
                if len(pcts) > 1:
                    grat['percentual'] = f"{pcts[0]}% a {pcts[1]}%"

            dados['gratificacoes'].append(grat)

    # Remuneração total
    m = re.search(r'(?:remuneração|retribuição)\s*(?:total|inicial|bruta)\s*.*?R\$\s*([\d.]+,\d{2})', texto, re.IGNORECASE)
    if m:
        dados['remuneracao_total_inicial'] = float(m.group(1).replace('.', '').replace(',', '.'))

    return dados


def extrair_beneficios(texto: str) -> dict:
    """Extrai benefícios."""
    dados = {}

    padroes = {
        'aux_alimentacao': [
            r'(?:auxílio|vale)[\s\-]*(?:alimentação|refeição)\s*.*?R\$\s*([\d.]+,\d{2})',
            r'(?:alimentação|refeição)\s*.*?R\$\s*([\d.]+,\d{2})',
        ],
        'aux_saude': [
            r'(?:auxílio|assistência)[\s\-]*(?:saúde|médic)\s*.*?R\$\s*([\d.]+,\d{2})',
        ],
        'aux_creche': [
            r'(?:auxílio|assistência)[\s\-]*(?:creche|pré[\s\-]*escolar)\s*.*?R\$\s*([\d.]+,\d{2})',
        ],
    }

    for campo, lista_padroes in padroes.items():
        for padrao in lista_padroes:
            m = re.search(padrao, texto, re.IGNORECASE)
            if m:
                dados[campo] = float(m.group(1).replace('.', '').replace(',', '.'))
                break

    return dados


def extrair_vagas(texto: str, cargo: str) -> dict:
    """Extrai informações de vagas."""
    dados = {}

    # Total de vagas
    m = re.search(r'(\d+)\s*vaga', texto, re.IGNORECASE)
    if m:
        dados['vagas_total'] = int(m.group(1))

    # Jornada
    m = re.search(r'(\d+)\s*horas?\s*semana', texto, re.IGNORECASE)
    if m:
        dados['jornada_semanal'] = f"{m.group(1)} horas semanais"

    # Regime
    if 'CLT' in texto or 'Consolidação das Leis' in texto:
        dados['regime'] = 'CLT'
    elif 'estatutário' in texto.lower() or 'regime jurídico único' in texto.lower():
        dados['regime'] = 'Estatutário'

    return dados


def extrair_titulacao(texto: str) -> dict:
    """Extrai informações de titulação/qualificação."""
    dados = {}

    # Percentuais de titulação
    padroes = {
        'especializacao_percentual': r'(?:especialização|pós[\s\-]*graduação)\s*.*?(\d+(?:,\d+)?)\s*%',
        'mestrado_percentual': r'mestrado\s*.*?(\d+(?:,\d+)?)\s*%',
        'doutorado_percentual': r'doutorado\s*.*?(\d+(?:,\d+)?)\s*%',
    }

    for campo, padrao in padroes.items():
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            dados[campo] = float(m.group(1).replace(',', '.'))

    return dados


# ─────────────────────────── DADOS FALTANTES ─────────────────────────────

CAMPOS_OBRIGATORIOS = [
    ('orgao', 'Nome completo do órgão'),
    ('sigla', 'Sigla do órgão'),
    ('cargo', 'Cargo analisado'),
    ('banca', 'Banca organizadora'),
    ('regime', 'Regime jurídico (Estatutário/CLT)'),
    ('jornada_semanal', 'Jornada semanal'),
    ('remuneracao.vencimento_base', 'Vencimento base inicial (R$)'),
    ('remuneracao.remuneracao_total_inicial', 'Remuneração total inicial (R$)'),
    ('beneficios.aux_alimentacao', 'Auxílio alimentação (R$/mês)'),
    ('notas.remuneracao', 'Nota remuneração (0-10)'),
    ('notas.beneficios', 'Nota benefícios (0-10)'),
    ('notas.crescimento', 'Nota crescimento (0-10)'),
    ('notas.qualidade_vida', 'Nota qualidade de vida (0-10)'),
    ('notas.flexibilidade', 'Nota flexibilidade (0-10)'),
    ('notas.estabilidade', 'Nota estabilidade (0-10)'),
    ('notas.valorizacao_ti', 'Nota valorização TI (0-10)'),
    ('notas.localizacao', 'Nota localização (0-10)'),
]


def identificar_faltantes(dados: dict) -> list:
    """Identifica campos obrigatórios que não foram preenchidos."""
    faltantes = []
    for campo, descricao in CAMPOS_OBRIGATORIOS:
        partes = campo.split('.')
        valor = dados
        for p in partes:
            if isinstance(valor, dict):
                valor = valor.get(p)
            else:
                valor = None
                break
        if valor is None or valor == '' or valor == 0:
            faltantes.append({'campo': campo, 'descricao': descricao})
    return faltantes


def perguntar_faltantes(faltantes: list, dados: dict) -> dict:
    """Pergunta ao usuário os dados que faltam."""
    if not faltantes:
        return dados

    print("\n" + "="*60)
    print("📋 DADOS NÃO ENCONTRADOS NO EDITAL")
    print("   Preencha abaixo ou pressione ENTER para pular:")
    print("="*60 + "\n")

    for item in faltantes:
        campo = item['campo']
        desc = item['descricao']
        resp = input(f"  {desc}: ").strip()

        if resp:
            # Converter números
            partes = campo.split('.')
            try:
                val = float(resp)
            except ValueError:
                val = resp

            # Definir no dict aninhado
            ref = dados
            for p in partes[:-1]:
                if p not in ref:
                    ref[p] = {}
                ref = ref[p]
            ref[partes[-1]] = val

    return dados


# ─────────────────────────── GERADOR DE MARKDOWN ─────────────────────────

def gerar_slug(orgao: str, cargo: str, ano: int) -> str:
    """Gera slug para o arquivo."""
    import unicodedata
    texto = f"{orgao}-{ano}-{cargo}"
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'[^\w\s-]', '', texto.lower())
    texto = re.sub(r'[-\s]+', '-', texto).strip('-')
    return texto[:60]


def gerar_markdown(dados: dict, slug: str) -> str:
    """Gera arquivo Markdown com front-matter YAML."""
    front_matter = yaml.dump(dados, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    md = f"""---
{front_matter}---

## Análise do Edital

**Órgão:** {dados.get('orgao', 'N/D')}  
**Cargo:** {dados.get('cargo', 'N/D')}  
**Banca:** {dados.get('banca', 'N/D')}  
**Edital:** {dados.get('edital_numero', 'N/D')} ({dados.get('edital_ano', 'N/D')})  

### Remuneração

| Componente | Valor |
|:-----------|------:|
| Vencimento Base | R$ {dados.get('remuneracao', {}).get('vencimento_base', 'N/D'):,.2f} |
"""

    # Gratificações
    for grat in dados.get('remuneracao', {}).get('gratificacoes', []):
        nome = grat.get('nome', '')
        val = grat.get('valor_inicial', 'N/D')
        if isinstance(val, (int, float)):
            md += f"| {nome} (inicial) | R$ {val:,.2f} |\n"
        else:
            md += f"| {nome} | {val} |\n"

    total = dados.get('remuneracao', {}).get('remuneracao_total_inicial')
    if total:
        md += f"| **Total Inicial** | **R$ {total:,.2f}** |\n"

    md += "\n### Benefícios\n\n"
    beneficios = dados.get('beneficios', {})
    if beneficios.get('aux_alimentacao'):
        md += f"- Auxílio Alimentação: R$ {beneficios['aux_alimentacao']:,.2f}\n"
    if beneficios.get('aux_saude'):
        md += f"- Auxílio Saúde: R$ {beneficios['aux_saude']:,.2f}\n"
    if beneficios.get('plano_saude'):
        md += f"- Plano de Saúde: {beneficios['plano_saude']}\n"

    # Dados faltantes
    faltantes = dados.get('dados_faltantes', [])
    if faltantes:
        md += "\n### ⚠️ Dados Pendentes\n\n"
        md += "Os seguintes campos não foram encontrados automaticamente:\n\n"
        for f in faltantes:
            md += f"- [ ] {f['descricao']} (`{f['campo']}`)\n"

    return md


# ─────────────────────────── MAIN ───────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("═══════════════════════════════════════════════════════")
        print("  📄 ANALISADOR DE EDITAIS DE CONCURSO")
        print("═══════════════════════════════════════════════════════")
        print()
        print("Uso:")
        print('  python scripts/processar_edital.py <edital.pdf> [--cargo "Nome"]')
        print()
        print("Exemplo:")
        print('  python scripts/processar_edital.py editais/tjce-2026.pdf --cargo "Analista Judiciário"')
        print()
        sys.exit(0)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    # Cargo via argumento
    cargo_escolhido = None
    if '--cargo' in sys.argv:
        idx = sys.argv.index('--cargo')
        if idx + 1 < len(sys.argv):
            cargo_escolhido = sys.argv[idx + 1]

    print(f"\n📄 Processando: {pdf_path}")
    print("   Extraindo texto...")

    texto = extrair_texto_pdf(pdf_path)
    print(f"   ✅ {len(texto)} caracteres extraídos")

    # Identificar cargos
    if not cargo_escolhido:
        cargos = encontrar_cargos(texto)
        if cargos:
            print(f"\n📋 Cargos encontrados ({len(cargos)}):")
            for i, c in enumerate(cargos[:20], 1):
                print(f"   {i}. {c}")
            print()
            escolha = input("Qual cargo analisar? (número ou nome): ").strip()
            try:
                idx = int(escolha) - 1
                cargo_escolhido = cargos[idx]
            except (ValueError, IndexError):
                cargo_escolhido = escolha
        else:
            cargo_escolhido = input("\n❓ Não encontrei cargos automaticamente. Qual cargo analisar? ").strip()

    print(f"\n🎯 Cargo selecionado: {cargo_escolhido}")
    print("   Extraindo dados...")

    # Extrair todos os dados
    dados_orgao = extrair_orgao(texto)
    dados_remuneracao = extrair_remuneracao(texto, cargo_escolhido)
    dados_beneficios = extrair_beneficios(texto)
    dados_vagas = extrair_vagas(texto, cargo_escolhido)
    dados_titulacao = extrair_titulacao(texto)

    # Montar estrutura completa
    ano = date.today().year
    dados = {
        'id': '',
        'status': 'parcial',
        'data_processamento': date.today().strftime('%d/%m/%Y'),
        'edital_arquivo': os.path.basename(pdf_path),
        'orgao': dados_orgao.get('orgao', ''),
        'sigla': dados_orgao.get('sigla', ''),
        'esfera': '',
        'estado': '',
        'cidade': '',
        'banca': dados_orgao.get('banca', ''),
        'edital_numero': '',
        'edital_ano': ano,
        'edital_link': '',
        'cargo': cargo_escolhido,
        'area': '',
        'escolaridade': 'Nível Superior',
        'vagas_total': dados_vagas.get('vagas_total'),
        'regime': dados_vagas.get('regime', ''),
        'jornada_semanal': dados_vagas.get('jornada_semanal', ''),
        'local_trabalho': '',
        'remuneracao': dados_remuneracao,
        'beneficios': dados_beneficios,
        'carreira': {},
        'titulacao': dados_titulacao,
        'trabalho': {},
        'localizacao': {},
        'notas': {},
        'fontes': [{
            'tipo': 'Oficial',
            'descricao': f'Edital {os.path.basename(pdf_path)}',
            'link': '',
            'data': date.today().strftime('%d/%m/%Y'),
        }],
        'dados_faltantes': [],
    }

    # Identificar faltantes
    faltantes = identificar_faltantes(dados)
    dados['dados_faltantes'] = faltantes

    # Mostrar resumo
    print("\n" + "="*60)
    print("📊 RESUMO DA EXTRAÇÃO")
    print("="*60)
    print(f"   Órgão:       {dados['orgao'] or '❌ não encontrado'}")
    print(f"   Sigla:       {dados['sigla'] or '❌ não encontrado'}")
    print(f"   Cargo:       {dados['cargo']}")
    print(f"   Banca:       {dados['banca'] or '❌ não encontrada'}")
    print(f"   Regime:      {dados['regime'] or '❌ não encontrado'}")
    vb = dados['remuneracao'].get('vencimento_base')
    print(f"   Venc. Base:  {'R$ ' + f'{vb:,.2f}' if vb else '❌ não encontrado'}")
    rt = dados['remuneracao'].get('remuneracao_total_inicial')
    print(f"   Remun.Total: {'R$ ' + f'{rt:,.2f}' if rt else '❌ não encontrado'}")
    grats = dados['remuneracao'].get('gratificacoes', [])
    if grats:
        for g in grats:
            print(f"   Gratif:      {g['nome']} = R$ {g.get('valor_inicial', '?')}")
    aux_al = dados['beneficios'].get('aux_alimentacao')
    print(f"   Aux.Alim:    {'R$ ' + f'{aux_al:,.2f}' if aux_al else '❌ não encontrado'}")
    print(f"\n   ⚠️  Dados faltantes: {len(faltantes)} campos")
    print("="*60)

    # Perguntar faltantes
    if faltantes:
        resp = input("\n❓ Deseja preencher os dados faltantes agora? (s/N): ").strip().lower()
        if resp in ('s', 'sim', 'y', 'yes'):
            dados = perguntar_faltantes(faltantes, dados)
            # Recalcular faltantes
            dados['dados_faltantes'] = identificar_faltantes(dados)

    # Atualizar status
    if not dados['dados_faltantes']:
        dados['status'] = 'completo'
    elif len(dados['dados_faltantes']) < 5:
        dados['status'] = 'parcial'

    # Gerar slug e salvar
    slug = gerar_slug(
        dados.get('sigla') or dados.get('orgao', 'concurso'),
        dados.get('cargo', 'cargo'),
        dados.get('edital_ano', ano)
    )
    dados['id'] = slug

    arquivo_md = CONTENT_DIR / f"{slug}.md"
    conteudo = gerar_markdown(dados, slug)

    with open(arquivo_md, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    print(f"\n✅ Arquivo gerado: {arquivo_md}")
    print(f"   Status: {dados['status']}")
    if dados['dados_faltantes']:
        print(f"   ⚠️  {len(dados['dados_faltantes'])} campos pendentes (edite o .md ou use o site)")
    print(f"\n💡 Para publicar: git add . && git commit -m 'Adiciona edital {slug}' && git push")


if __name__ == '__main__':
    main()
