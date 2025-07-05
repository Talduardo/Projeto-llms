import os
import joblib
import re
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# --- Configurações Iniciais ---
# Configurar Pandas para não truncar a saída de .to_string()
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 160)
pd.set_option('display.max_colwidth', 50)

# Carregar as chaves da API via .env
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY não encontrada no arquivo .env ou nas variáveis de ambiente.")

# Inicializar o cliente da OpenAI
client = OpenAI(api_key=openai_api_key)

# Modelo OpenAI Fixo para os testes
MODELO_ID_FIXO = "gpt-4o-mini"
NOME_SUBPASTA_MODELO = "gpt4mini" # Nome da subpasta para os resultados

# Diretórios Base
base_dir = Path(__file__).resolve().parent
# Ajuste conforme a estrutura do seu projeto. 'util/data' parece ser o caminho correto para .z
# Se os arquivos CSV estiverem em outro local, ajuste o caminho conforme necessário.
# Certifique-se de que o diretório 'util/data' contém os arquivos .z necessários
# Para este código, estou focando na leitura de .z como a principal fonte de dados contábeis estruturados.
data_dir_z = base_dir.parent.parent / 'util' / 'data'
relatorio_dir_base = base_dir / 'task18_resultados' # Pasta principal de saída

# --- Funções de Leitura de Dados ---

def ler_arquivo_csv(caminho_arquivo: Path) -> str | None:
    """
    Lê o conteúdo de um arquivo CSV e retorna como uma string.
    Retorna None em caso de erro ou arquivo não encontrado.
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo CSV não encontrado: '{caminho_arquivo}'")
        return None
    except Exception as e:
        print(f"Erro ao ler arquivo CSV: '{caminho_arquivo}'. Erro: {e}")
        return None

def carregar_e_processar_dados_para_llm(data_dir: Path) -> str:
    """
    Carrega arquivos .z (DataFrames) de um diretório, aplica uma estratégia de redução
    e retorna o conteúdo como uma string formatada para inclusão no prompt do LLM.
    """
    arquivos_z = list(data_dir.glob('*.z'))
    dados = {}
    if not arquivos_z:
        print(f"⚠️ Nenhum arquivo .z encontrado em {data_dir}. O conteúdo dos dados estará vazio.")
    else:
        print(f"Arquivos .z encontrados em {data_dir}:")
        for arquivo in arquivos_z:
            print(f"  - {arquivo.name}")
            try:
                dados[arquivo.name] = joblib.load(arquivo)
            except Exception as e:
                print(f"  ❌ Erro ao carregar {arquivo.name}: {e}")

    conteudo_dados = "### DADOS A SEREM ANALISADOS ###\n\n"
    print("\n🔄 Processando DataFrames para inclusão no prompt (estratégia de redução agressiva)...")

    ROWS_SMALL_DF = 75
    ROWS_MEDIUM_DF_HEADTAIL = 15
    ROWS_LARGE_DF_HEADTAIL = 10
    ROWS_VERY_LARGE_DF_HEADTAIL = 5

    for nome, df_content in dados.items():
        df_shape = df_content.shape if hasattr(df_content, 'shape') else (0,0)
        conteudo_dados += f"### Arquivo: {nome} (Shape: {df_shape}) ###\n"

        if not hasattr(df_content, 'to_string') or not hasattr(df_content, 'describe'):
            print(f"  📄 Conteúdo não é DataFrame ou não tem os métodos esperados (convertendo como string genérica): {nome}")
            conteudo_dados += str(df_content)
            conteudo_dados += "\n\n"
            continue

        num_rows = df_shape[0]

        if num_rows <= ROWS_SMALL_DF:
            print(f"  📄 Incluindo DataFrame completo (<= {ROWS_SMALL_DF} linhas): {nome}")
            conteudo_dados += df_content.to_string()
        else:
            head_n, tail_n = ROWS_LARGE_DF_HEADTAIL, ROWS_LARGE_DF_HEADTAIL
            if num_rows <= 200:
                head_n, tail_n = ROWS_MEDIUM_DF_HEADTAIL, ROWS_MEDIUM_DF_HEADTAIL
            elif num_rows > 3000:
                head_n, tail_n = ROWS_VERY_LARGE_DF_HEADTAIL, ROWS_VERY_LARGE_DF_HEADTAIL

            print(f"  📄 Incluindo head({head_n}), tail({tail_n}) e describe() para: {nome}")
            conteudo_dados += f"--- INÍCIO DAS PRIMEIRAS {head_n} LINHAS DE {nome} ---\n"
            conteudo_dados += df_content.head(head_n).to_string()
            conteudo_dados += f"\n--- FIM DAS PRIMEIRAS {head_n} LINHAS DE {nome} ---\n\n"

            conteudo_dados += f"--- INÍCIO DAS ÚLTIMAS {tail_n} LINHAS DE {nome} ---\n"
            conteudo_dados += df_content.tail(tail_n).to_string()
            conteudo_dados += f"\n--- FIM DAS ÚLTIMAS {tail_n} LINHAS DE {nome} ---\n\n"

            try:
                conteudo_dados += f"--- RESUMO ESTATÍSTICO (DESCRIBE) DE {nome} ---\n"
                conteudo_dados += df_content.describe(include='all').to_string()
                conteudo_dados += f"\n--- FIM DO RESUMO ESTATÍSTICO DE {nome} ---\n"
            except Exception as e:
                print(f"    ⚠️ Não foi possível gerar describe() para {nome}: {e}")
                conteudo_dados += f"--- RESUMO ESTATÍSTICO (DESCRIBE) DE {nome} INDISPONÍVEL ---\n"

        conteudo_dados += "\n\n"

    tamanho_estimado_conteudo_dados_bytes = len(conteudo_dados.encode('utf-8'))
    tamanho_estimado_conteudo_dados_kb = tamanho_estimado_conteudo_dados_bytes / 1024
    tokens_estimados_dados = tamanho_estimado_conteudo_dados_bytes / 4

    print(f"ℹ️ Tamanho estimado do 'conteudo_dados' (estratégia agressiva): {tamanho_estimado_conteudo_dados_kb:.2f} KB")
    print(f"ℹ️ Tokens estimados para 'conteudo_dados' (aprox.): {tokens_estimados_dados:.0f} tokens")
    print("  GPT-4o-mini tem um grande contexto (128k tokens), mas é bom monitorar o uso de tokens para custos e performance.")

    return conteudo_dados


# --- Prompts Comparativos ---
prompts_comparativos = {
    "prompt1": """Com base nos dados fornecidos, elabore um único resumo conciso contendo quatro seções:

1. Fluxo de Caixa Operacional
2. Desempenho de Vendas por Categoria
3. Liquidez da Empresa
4. Principais Gastos – maiores centros de custo e variação relevante.

Use linguagem direta, sem jargões desnecessários, focada em decisões rápidas.""",
    "prompt2": """Você é um Analista Financeiro Sênior encarregado de preparar um briefing executivo para a diretoria. Com base nos dados financeiros fornecidos (incluindo categorias, contas a pagar, contas a receber, movimento financeiro, naturezas financeiras, produtos e vendas):
1. Sumário Executivo: Apresente um panorama geral da saúde financeira da empresa, considerando a interação entre vendas, custos (implícitos nas contas a pagar e naturezas financeiras) e o fluxo de caixa (movimento financeiro).
2. Indicadores Chave (KPIs): Destaque os 3-5 KPIs mais relevantes. Considere:
    * Rentabilidade por produto ou categoria (cruzando df_vendas, df_produtos, df_categorias).
    * Ciclo de conversão de caixa (analisando prazos de df_contas_a_receber e df_contas_a_pagar).
    * Níveis de inadimplência (de df_contas_a_receber).
    * Concentração de vendas (em produtos ou categorias).
3. Principais Riscos e Alertas: Identifique de 2 a 3 riscos financeiros ou operacionais críticos. Analise:
    * Riscos de liquidez com base no movimento financeiro e nas obrigações de contas a pagar versus recebíveis.
    * Dependência excessiva de poucos produtos ou categorias (df_produtos, df_categorias, df_vendas).
    * Aumento de despesas específicas (df_naturezas_financeiras, df_contas_a_pagar).
4. Recomendações Estratégicas: Sugira de 1 a 2 ações prioritárias para mitigar riscos ou capitalizar oportunidades, referenciando quais áreas (vendas, gestão de pagamentos/recebimentos, etc.) seriam impactadas.
Utilize bullet points para clareza e uma linguagem direta e focada na tomada de decisão."""
}

# --- Funções de Geração de Resumo ---

def enviar_prompt_para_llm(user_prompt_content: str, model_id: str = MODELO_ID_FIXO) -> str:
    """
    Envia um prompt para o Modelo de Linguagem Grande (LLM) da OpenAI e retorna a resposta.
    """
    system_message = "Você é um especialista contábil e financeiro altamente qualificado, capaz de adaptar seu estilo de comunicação e análise conforme solicitado."
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt_content}
    ]

    params = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 4096, # Um valor alto para garantir espaço para a resposta
        "temperature": 0.3,
        "top_p": 0.9
    }

    try:
        chat_completion = client.chat.completions.create(**params)
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        error_details_str = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                if 'error' in error_data:
                    error_details_str += f" (API Error: {error_data['error']})"
            except:
                pass
        elif hasattr(e, 'body') and e.body is not None:
            error_details_str += f" (Error Body: {e.body})"

        print(f"  ❌ Erro ao chamar a API da OpenAI: {e}")
        print(f"    Detalhes do erro: {error_details_str}")
        if "context_length_exceeded" in error_details_str.lower() or \
           "prompt is too long" in error_details_str.lower() or \
           "tokens" in error_details_str.lower():
            print("  ‼️ ERRO: O PROMPT PROVAVELMENTE EXCEDEU O TAMANHO MÁXIMO DE CONTEXTO/REQUISIÇÃO DO MODELO! ‼️")
            print("  Considere reduzir MAIS AINDA a quantidade de dados enviados ou usar uma estratégia de sumarização mais agressiva.")
        return "Erro ao gerar resumo."

def gerar_resumo_contabil_hibrido(dados_processados: str, prompt_base_tipo: str, prompt_refinador_tipo: str) -> str:
    """
    Gera um resumo contábil usando a abordagem híbrida:
    1. Aplica o prompt base para extração primária.
    2. Alimenta o resultado ao prompt refinador para detalhes estratégicos.
    """
    # 1. Aplicação do Prompt Base (Prompt 1 para extração e padronização)
    prompt_1_texto = prompts_comparativos[prompt_base_tipo]
    prompt_1_final = f"{prompt_1_texto}\n\nDados:\n{dados_processados}"
    print(f"\n--- Gerando Resumo Base com '{prompt_base_tipo}' ---")
    resumo_base = enviar_prompt_para_llm(prompt_1_final)
    print(f"\nResumo Base Gerado:\n{resumo_base[:500]}...") # Exibe uma parte do resumo base

    if "Erro ao gerar resumo." in resumo_base:
        return "Erro na geração do resumo base. Abortando processo híbrido."

    # 2. Aplicação do Prompt Refinador (Prompt 2 para enriquecimento estratégico)
    prompt_2_texto = prompts_comparativos[prompt_refinador_tipo]
    prompt_2_final = f"{prompt_2_texto}\n\nAnalise o seguinte resumo inicial e os dados originais para enriquecer a resposta:\n\nResumo Inicial:\n{resumo_base}\n\nDados Originais:\n{dados_processados}"
    print(f"\n--- Refinando Resumo com '{prompt_refinador_tipo}' ---")
    resumo_final_hibrido = enviar_prompt_para_llm(prompt_2_final)
    print(f"\nResumo Refinado Gerado:\n{resumo_final_hibrido[:500]}...") # Exibe uma parte do resumo refinado

    return resumo_final_hibrido

# --- Função Principal ---

def main():
    if not openai_api_key:
        print("Erro: A chave da API do OpenAI não foi configurada. Certifique-se de ter um arquivo .env com OPENAI_API_KEY.")
        return

    # Carrega e processa os dados dos arquivos .z
    conteudo_dados_llm = carregar_e_processar_dados_para_llm(data_dir_z)

    if not conteudo_dados_llm.strip():
        print("Nenhum conteúdo de dados foi carregado ou processado. Encerrando.")
        return

    print("\n--- Escolha a Abordagem para o Resumo Contábil ---")
    print("1: Prompt 1 (Análise Setorial Concisa) - Ideal para relatórios operacionais diários.")
    print("2: Prompt 2 (Briefing Executivo Estratégico) - Ideal para análises mais profundas e estratégicas.")
    print("3: Abordagem Híbrida (Prompt 1 como base, Prompt 2 como refinador) - Recomendado para resultados otimizados.")
    print("0: Sair")

    while True:
        escolha = input("Digite o número da sua escolha: ")

        resumo_gerado = None
        nome_tipo_resumo = ""

        if escolha == '1':
            nome_tipo_resumo = "Prompt1_Conciso"
            resumo_gerado = enviar_prompt_para_llm(f"{prompts_comparativos['prompt1']}\n\nDados:\n{conteudo_dados_llm}")
        elif escolha == '2':
            nome_tipo_resumo = "Prompt2_Estrategico"
            resumo_gerado = enviar_prompt_para_llm(f"{prompts_comparativos['prompt2']}\n\nDados:\n{conteudo_dados_llm}")
        elif escolha == '3':
            nome_tipo_resumo = "Hibrido_P1_P2"
            resumo_gerado = gerar_resumo_contabil_hibrido(conteudo_dados_llm, "prompt1", "prompt2")
        elif escolha == '0':
            print("Saindo do programa.")
            return
        else:
            print("Opção inválida. Por favor, digite 1, 2, 3 ou 0.")
            continue

        if resumo_gerado and "Erro ao gerar resumo." not in resumo_gerado:
            print("\n--- Resumo Gerado ---")
            print(resumo_gerado)

            # Salvar o resumo
            relatorio_dir_modelo_especifico = relatorio_dir_base / NOME_SUBPASTA_MODELO
            relatorio_dir_modelo_especifico.mkdir(parents=True, exist_ok=True)
            nome_arquivo_resumo = relatorio_dir_modelo_especifico / f"{nome_tipo_resumo}_resultado.txt"
            with open(nome_arquivo_resumo, "w", encoding="utf-8") as arquivo:
                arquivo.write(f"Modelo Utilizado: {MODELO_ID_FIXO}\n\n")
                arquivo.write(f"--- {nome_tipo_resumo.upper()} ---\n")
                if escolha == '1':
                    arquivo.write(f"Instrução do Prompt:\n{prompts_comparativos['prompt1']}\n\n")
                elif escolha == '2':
                    arquivo.write(f"Instrução do Prompt:\n{prompts_comparativos['prompt2']}\n\n")
                elif escolha == '3':
                    arquivo.write(f"Instrução do Prompt Base (P1):\n{prompts_comparativos['prompt1']}\n\n")
                    arquivo.write(f"Instrução do Prompt Refinador (P2):\n{prompts_comparativos['prompt2']}\n\n")
                arquivo.write("--- RESPOSTA DO MODELO ---\n")
                arquivo.write(resumo_gerado)
            print(f"\nO resumo foi salvo em '{nome_arquivo_resumo}'.")
        else:
            print(f"\nNão foi possível gerar o resumo para a opção {escolha}.")

        # Perguntar se o usuário quer gerar outro resumo
        continuar = input("\nGerar outro resumo? (s/n): ").lower()
        if continuar != 's':
            print("Encerrando o programa.")
            break

if __name__ == "__main__":
    main()