---
# ═══════════════════════════════════════════════════════════════════════
# SCHEMA GENÉRICO DE EDITAL DE CONCURSO
# Todo arquivo .md em content/editais/ deve seguir este formato.
# O script de processamento preenche automaticamente o que encontra
# e marca como "pendente" o que não consegue extrair.
# ═══════════════════════════════════════════════════════════════════════

# ── METADADOS ──
id: ""                          # slug único (ex: tjce-2026-analista-ti)
status: "pendente"              # pendente | parcial | completo
data_processamento: ""          # data que o edital foi processado
edital_arquivo: ""              # nome do PDF original

# ── IDENTIFICAÇÃO DO CONCURSO ──
orgao: ""                       # Nome completo do órgão
sigla: ""                       # Sigla (ex: TJCE, IPECE)
esfera: ""                      # Federal | Estadual | Municipal | Empresa Pública
estado: ""                      # UF
cidade: ""                      # Cidade sede
banca: ""                       # Banca organizadora
edital_numero: ""               # Número do edital (ex: Edital nº 01/2026)
edital_ano: null                # Ano do edital
edital_link: ""                 # URL do edital PDF
inscricoes_inicio: ""           # Data início inscrições
inscricoes_fim: ""              # Data fim inscrições
prova_data: ""                  # Data da prova

# ── CARGO SELECIONADO ──
cargo: ""                       # Nome do cargo
area: ""                        # Área/especialidade
escolaridade: ""                # Nível Superior / Médio / Técnico
formacao_exigida: ""            # Formação específica exigida
vagas_total: null               # Total de vagas
vagas_ampla: null               # Vagas ampla concorrência
vagas_pcd: null                 # Vagas PCD
vagas_cotas: null               # Vagas cotas raciais

# ── REGIME E JORNADA ──
regime: ""                      # Estatutário | CLT | Emprego Público
jornada_semanal: ""             # Ex: "40 horas semanais"
local_trabalho: ""              # Onde vai trabalhar

# ── REMUNERAÇÃO ──
remuneracao:
  vencimento_base: null              # Vencimento/salário base (R$)
  gratificacoes:                     # Lista de gratificações
    - nome: ""                       # Nome da gratificação (GAM, GDAP, GDE, etc.)
      valor_inicial: null            # Valor inicial (R$)
      valor_maximo: null             # Valor máximo (R$)
      percentual: ""                 # Percentual (ex: "30% a 60%")
      base_calculo: ""              # Sobre o quê incide
      observacao: ""                 # Obs adicional
  remuneracao_total_inicial: null    # Total inicial (venc + gratificações)
  remuneracao_total_maxima: null     # Total com gratificação máxima
  teto_remuneratorio: null           # Teto constitucional aplicável

# ── BENEFÍCIOS ──
beneficios:
  aux_alimentacao: null              # Auxílio alimentação (R$/mês)
  aux_refeicao: null                 # Auxílio refeição (R$/mês)
  aux_saude: null                    # Auxílio saúde (R$/mês)
  plano_saude: ""                    # Descrição do plano de saúde
  plano_odonto: ""                   # Plano odontológico
  aux_transporte: ""                 # Auxílio transporte
  aux_creche: null                   # Auxílio creche/pré-escolar (R$)
  previdencia_complementar: ""       # Previdência complementar
  plr: ""                            # PLR/PPR
  seguro_vida: ""                    # Seguro de vida
  outros: ""                         # Outros benefícios

# ── CARREIRA E PROGRESSÃO ──
carreira:
  plano_nome: ""                     # Nome do plano de cargos/carreira
  classes: ""                        # Classes/faixas existentes
  niveis: null                       # Número de níveis/padrões
  progressao_horizontal: ""          # Como funciona (mérito, tempo, etc.)
  progressao_vertical: ""            # Promoção de classe
  tempo_minimo_progressao: ""        # Interstício mínimo
  criterios: ""                      # Critérios para progressão
  avaliacao_desempenho: ""           # Como é a avaliação

# ── TITULAÇÃO / QUALIFICAÇÃO ──
titulacao:
  especializacao_percentual: null    # % adicional por especialização
  especializacao_valor: null         # Valor adicional (R$)
  mestrado_percentual: null          # % adicional por mestrado
  mestrado_valor: null               # Valor adicional (R$)
  doutorado_percentual: null         # % adicional por doutorado
  doutorado_valor: null              # Valor adicional (R$)
  base_calculo: ""                   # Sobre qual valor incide o %
  certificacoes: ""                  # Certificações valorizadas
  observacoes: ""                    # Regras específicas

# ── TRABALHO E QUALIDADE DE VIDA ──
trabalho:
  home_office: ""                    # Sim / Não / Parcial
  teletrabalho_regulamentado: ""     # Base legal se houver
  dias_remotos: ""                   # Quantos dias/semana
  flexibilidade_horario: ""          # Descrição
  banco_horas: ""                    # Sim/Não
  plantao_sobreaviso: ""             # Descrição

# ── LOCALIZAÇÃO ──
localizacao:
  endereco: ""                       # Endereço do órgão
  bairro: ""                         # Bairro
  cidade: ""                         # Cidade
  transporte_publico: ""             # Acessibilidade
  estacionamento: ""                 # Tem?
  observacoes: ""                    # Notas adicionais

# ── NOTAS DE AVALIAÇÃO (0-10) ──
# Preenchidas manualmente ou calculadas pelo sistema
notas:
  remuneracao: null
  beneficios: null
  crescimento: null
  qualidade_vida: null
  flexibilidade: null
  estabilidade: null
  valorizacao_ti: null
  localizacao: null

# ── FONTES ──
fontes:
  - tipo: ""          # Oficial | Secundária
    descricao: ""     # O que foi consultado
    link: ""          # URL
    data: ""          # Data da consulta

# ── DADOS FALTANTES ──
# O sistema preenche automaticamente esta lista com os campos que não
# conseguiu extrair do edital. Aparece como formulário no site.
dados_faltantes: []
---

<!-- 
  Abaixo do front-matter, escreva observações, análise qualitativa,
  pontos de atenção do edital, etc. em Markdown livre.
-->
