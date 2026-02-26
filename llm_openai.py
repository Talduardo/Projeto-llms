import pandas as pd
import os
import openai
from unittest.mock import patch
import unittest
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém a chave da API do OpenAI do arquivo .env
openai.api_key = os.getenv("OPENAI_API_KEY")

def enviar_prompt_para_llm(prompt):
    """
    Envia um prompt para um Modelo de Linguagem Grande (LLM) da OpenAI e retorna a resposta.
    Tenta enviar o prompt para a API da OpenAI (gpt-3.5-turbo) e retorna o texto da resposta.

    Note: 'gpt-3.5-turbo' é um modelo de chat e requer uma estrutura de mensagem diferente.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Erro ao chamar a API da OpenAI: {e}")
        return "Erro ao gerar resumo."

def carregar_dataframe(caminho_arquivo):
    """
    Carrega um DataFrame do pandas a partir de um arquivo CSV ou Excel.
    Verifica a extensão do arquivo para usar a função de leitura correta do pandas.
    Em caso de arquivo não encontrado ou outro erro de leitura, retorna None.
    """
    try:
        if caminho_arquivo.endswith('.csv'):
            return pd.read_csv(caminho_arquivo)
        elif caminho_arquivo.endswith(('.xlsx', '.xls')):
            return pd.read_excel(caminho_arquivo)
        else:
            raise ValueError(f"Formato de arquivo não suportado: '{caminho_arquivo}'")
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado: '{caminho_arquivo}'")
        return None
    except Exception as e:
        print(f"Erro ao carregar arquivo: '{caminho_arquivo}'. Erro: {e}")
        return None

def carregar_dataframes(arquivos_csv):
    """
    Carrega múltiplos DataFrames a partir de um dicionário de nomes de arquivos.
    Assume que os arquivos estão na pasta 'data' dentro de 'util', dois níveis acima
    do diretório do script.
    """
    dataframes = {}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pasta_arquivos = os.path.join(script_dir, '..', '..', 'util', 'data')
    for nome_arquivo, nome_df in arquivos_csv.items():
        caminho_absoluto = os.path.join(pasta_arquivos, nome_arquivo)
        df = carregar_dataframe(caminho_absoluto)
        if df is not None:
            dataframes[nome_df] = df
        else:
            print(f"Aviso: Não foi possível carregar DataFrame: '{nome_df}' de '{caminho_absoluto}'")
    return dataframes

def converter_dfs_para_texto(dataframes):
    """
    Converte um dicionário de DataFrames em uma única string formatada para o LLM.
    Cada DataFrame é limitado às primeiras linhas.
    DataFrames vazios são representados como tal.
    """
    return "\n".join(
        f"\n--- DataFrame: {nome} ---\n{df.head().to_string()}\n"
        if not df.empty
        else f"\n--- DataFrame: {nome} (vazio) ---\n"
        for nome, df in dataframes.items()
    )

def gerar_resumo_contabil(dataframes, prompt, usar_llm=True):
    """
    Gera um resumo contábil a partir de um conjunto de DataFrames, usando um LLM ou uma simulação.
    Prepara o prompt final incluindo os dados convertidos para texto.
    Se usar_llm for True, chama a API da OpenAI para gerar o resumo.
    Caso contrário, retorna um resumo simulado.
    """
    dados_para_llm = converter_dfs_para_texto(dataframes)
    if not dados_para_llm.strip():
        return "Erro: Nenhum dado contábil fornecido."

    prompt_final = f"{prompt}\n\nDados:\n{dados_para_llm}\nFormato de saída: Parágrafo único."

    print("\n--- Prompt Enviado para o LLM ---")
    print(prompt_final)

    if usar_llm:
        resumo = enviar_prompt_para_llm(prompt_final)
    else:
        resumo = "[[RESUMO CONTÁBIL GERADO PELO LLM]]"
    return resumo

def escolher_prompt():
    """
    Apresenta ao usuário uma lista de opções de prompts predefinidos.
    Permite que o usuário escolha uma opção digitando o número correspondente
    ou digite um prompt personalizado (opção 5).
    A opção 0 permite sair do programa.
    """
    print("\n--- Escolha o tipo de resumo contábil ---")
    print("1: Fluxo de Caixa")
    print("2: Vendas por Categoria")
    print("3: Liquidez")
    print("4: Gastos por Natureza")
    print("5: Prompt Personalizado")
    print("0: Sair")

    opcoes = {
        '1': """Você é um especialista em contabilidade. Analise os dados financeiros e gere um resumo conciso do fluxo de caixa operacional.""",
        '2': """Você é um especialista em análise de vendas. Analise os dados de vendas por categoria e destaque o desempenho.""",
        '3': """Você é um especialista em análise financeira. Resuma a liquidez da empresa com base nos dados financeiros.""",
        '4': """Você é um especialista em análise de custos. Resuma os principais tipos de gastos.""",
    }

    while True:
        opcao = input("Digite o número da opção: ")
        print(f"Opção digitada: '{opcao}'")  # Adicionado para debug
        if opcao in opcoes:
            return opcoes[opcao]
        elif opcao == '5':
            return input("Digite seu prompt personalizado: ")
        elif opcao == '0':
            print("Saindo.")
            return None
        else:
            print("Opção inválida. Tente novamente.")

def main():
    if not openai.api_key:
        print("Erro: A chave da API do OpenAI não foi configurada. Certifique-se de ter um arquivo .env com OPENAI_API_KEY.")
        return

    arquivos_csv = {
        "contas-a-pagar.csv": "df_contas_a_pagar",
        "contas-a-receber.csv": "df_contas_a_receber",
        "movimento-financeiro.csv": "df_movimento_financeiro",
        "naturezas-financeiras.csv": "df_naturezas_financeiras",
        'categorias.csv': 'df_categorias',
        'produtos.csv': 'df_produtos',
        'vendas.csv': 'df_vendas',
    }
    dataframes = carregar_dataframes(arquivos_csv)

    if dataframes:
        num_testes = 1  # Vamos gerar apenas um resumo por execução para simplificar aqui
        acertos_api = 0

        prompt = escolher_prompt()
        if prompt:
            resumo = gerar_resumo_contabil(dataframes, prompt)
            print("\n--- Resumo Gerado ---")
            print(resumo)

            # Salvar o resumo em um arquivo
            nome_arquivo_resumo = "resumo_api.txt"
            with open(nome_arquivo_resumo, "w") as arquivo:
                arquivo.write(resumo)
            print(f"\nO resumo da API foi salvo em '{nome_arquivo_resumo}'.")

            if resumo != "Erro ao gerar resumo.":
                acertos_api += 1

            taxa_acerto_api = (acertos_api / num_testes) * 100
            print(f"\nTaxa de 'acerto' da API (ausência de erro na última chamada): {taxa_acerto_api:.2f}%")
        else:
            print("Encerrando o programa.")
    else:
        print("Nenhum DataFrame foi carregado. Encerrando.")

### Testes ###

class TestGeradorResumoContabil(unittest.TestCase):
    def setUp(self):
        # Cria a estrutura de diretórios de teste na raiz (simulando a estrutura principal)
        os.makedirs("util/data", exist_ok=True)
        with open("util/data/teste.csv", "w") as f:
            f.write("Coluna1,Coluna2\n1,2\n3,4")
        df_test = pd.DataFrame({'Coluna1': [1, 3], 'Coluna2': [2, 4]})
        df_test.to_excel("util/data/teste.xlsx", index=False)
        with open("util/data/contas-a-pagar.csv", "w") as f:
            f.write("valor\n100\n200")
        with open("util/data/contas-a-receber.csv", "w") as f:
            f.write("valor\n50\n75")
        with open(".env", "w") as f:
            f.write("OPENAI_API_KEY=TEST_KEY")
        load_dotenv()

    def tearDown(self):
        # Limpa a estrutura de diretórios de teste
        if os.path.exists("util/data/teste.csv"):
            os.remove("util/data/teste.csv")
        if os.path.exists("util/data/teste.xlsx"):
            os.remove("util/data/teste.xlsx")
        if os.path.exists("util/data/contas-a-pagar.csv"):
            os.remove("util/data/contas-a-pagar.csv")
        if os.path.exists("util/data/contas-a-receber.csv"):
            os.remove("util/data/contas-a-receber.csv")
        if os.path.exists("util/data"):
            os.rmdir("util/data")
        if os.path.exists("util"):
            os.rmdir("util")
        if os.path.exists(".env"):
            os.remove(".env")

    def test_carregar_dataframe_csv(self):
        df = carregar_dataframe(os.path.join(os.getcwd(), 'util', 'data', 'teste.csv'))
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.shape, (2, 2))

    def test_carregar_dataframe_excel(self):
        df = carregar_dataframe(os.path.join(os.getcwd(), 'util', 'data', 'teste.xlsx'))
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.shape, (2, 2))

    def test_carregar_dataframes(self):
        arquivos_teste = {
            "contas-a-pagar.csv": "df_teste_pagar",
            "contas-a-receber.csv": "df_teste_receber",
        }
        # Aqui, nos testes, precisamos simular a estrutura correta
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pasta_arquivos_teste = os.path.join(script_dir, '..', '..', 'util', 'data')
        with patch('__main__.carregar_dataframe') as mock_carregar:
            mock_carregar.side_effect = lambda path: pd.DataFrame({'dummy': [1]}) if os.path.basename(path) in arquivos_teste else None
            dfs = carregar_dataframes(arquivos_teste)
            self.assertEqual(len(dfs), 2)
            self.assertIn("df_teste_pagar", dfs)
            self.assertIn("df_teste_receber", dfs)


if __name__ == "__main__":
    main()
