"""
convert_parquet_to_json.py
Converte os Parquets do Painel de Entregas da SDR para JSON
otimizado para consumo pelo painel HTML.

Uso:
    uv run convert_parquet_to_json.py
    python convert_parquet_to_json.py

Saída:
    data/agregado.json
    data/a_executar.json
    data/municipios.json
"""
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas",
#     "pyarrow",
# ]
# ///

import json
import os
import math
import pandas as pd

# ============================================================
# CONFIGURAÇÃO
# ============================================================
PASTA_SAIDA = "data"
ARQUIVOS = {
    "agregado": "agregado_detalhado_por_convenio_ano.parquet",
    "a_executar": "a_executar.parquet",
    "municipios": "classificacao_municipios_SDR.parquet",
}

# Colunas a manter de cada tabela (reduz tamanho do JSON)
COLUNAS_AGREGADO = [
    "data_carga", "UF_PROPONENTE", "COD_MUNIC_IBGE", "MUNIC_PROPONENTE",
    "NR_CONVENIO", "ANO_Convenio", "SIT_CONVENIO", "INSTRUMENTO_ATIVO",
    "MODALIDADE", "PROGRAMA", "ACAO", "ORIGEM_RECURSO",
    "VL_GLOBAL_CONV", "VL_REPASSE_CONV", "VL_DESEMBOLSADO_CONV",
    "ANO_pgto", "CATEGORIA_SUGERIDA", "CATEGORIA_ROTAS", "Divisao",
    "VALOR_AGREGADO", "QTD_AGREGADA", "KM_estimado",
]

COLUNAS_AEXECUTAR = [
    "data_carga", "ANO_Convenio", "NR_CONVENIO", "SIT_CONVENIO",
    "COD_MUNIC_IBGE", "MUNIC_PROPONENTE", "UF_PROPONENTE",
    "PROGRAMA", "ACAO",
    "MAX_VL_GLOBAL_CONV", "SOMA_VALOR_AGREGADO", "PERC_EXECUCAO", "VALOR_A_EXECUTAR",
]

COLUNAS_MUNICIPIOS = [
    "COD_MUNIC_IBGE", "nome", "sigla_uf", "nome_regiao",
    "Tipologia_PNDR_3", "População 2022",
    "amazonia_legal", "SUDENE", "semiarido", "faixa_fronteira",
    "matopiba", "cidades_intermediadoras", "amazonia_azul",
    "R_ACAI", "R_BIO", "R_CACAU", "R_CORDEIRO", "R_ECO_CIR",
    "R_FRUTI", "R_LEITE", "R_MEL", "R_TIC", "R_PESCADO",
    "R_MODA", "R_AVICULTURA", "R_MANDIOCULTURA",
]


# ============================================================
# UTILITÁRIOS
# ============================================================
def limpar_nan(obj):
    """Substitui NaN/Inf por None recursivamente."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: limpar_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [limpar_nan(v) for v in obj]
    return obj


def salvar_json(dados, caminho):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    dados_limpos = limpar_nan(dados)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados_limpos, f, ensure_ascii=False, separators=(",", ":"))
    tamanho = os.path.getsize(caminho) / (1024 * 1024)
    print(f"  ✓ {caminho} ({tamanho:.2f} MB)")


# ============================================================
# CONVERSÕES
# ============================================================
def converter_agregado():
    print("\n[1/3] Convertendo agregado_detalhado_por_convenio_ano.parquet...")
    df = pd.read_parquet(ARQUIVOS["agregado"])

    # Manter apenas colunas necessárias
    cols = [c for c in COLUNAS_AGREGADO if c in df.columns]
    df = df[cols].copy()

    # Garantir tipos corretos
    if "ANO_pgto" in df.columns:
        df["ANO_pgto"] = pd.to_numeric(df["ANO_pgto"], errors="coerce")
    if "COD_MUNIC_IBGE" in df.columns:
        df["COD_MUNIC_IBGE"] = pd.to_numeric(df["COD_MUNIC_IBGE"], errors="coerce")
    if "NR_CONVENIO" in df.columns:
        df["NR_CONVENIO"] = df["NR_CONVENIO"].astype(str)

    # Data de carga: manter apenas a primeira linha (string)
    if "data_carga" in df.columns:
        df["data_carga"] = df["data_carga"].astype(str).str[:19]

    print(f"  Linhas: {len(df)} | Colunas: {len(df.columns)}")
    dados = df.to_dict(orient="records")
    salvar_json(dados, os.path.join(PASTA_SAIDA, "agregado.json"))


def converter_a_executar():
    print("\n[2/3] Convertendo a_executar.parquet...")
    df = pd.read_parquet(ARQUIVOS["a_executar"])

    cols = [c for c in COLUNAS_AEXECUTAR if c in df.columns]
    df = df[cols].copy()

    if "COD_MUNIC_IBGE" in df.columns:
        df["COD_MUNIC_IBGE"] = pd.to_numeric(df["COD_MUNIC_IBGE"], errors="coerce")
    if "NR_CONVENIO" in df.columns:
        df["NR_CONVENIO"] = df["NR_CONVENIO"].astype(str)
    if "data_carga" in df.columns:
        df["data_carga"] = df["data_carga"].astype(str).str[:19]

    print(f"  Linhas: {len(df)} | Colunas: {len(df.columns)}")
    dados = df.to_dict(orient="records")
    salvar_json(dados, os.path.join(PASTA_SAIDA, "a_executar.json"))


def converter_municipios():
    print("\n[3/3] Convertendo classificacao_municipios_SDR.parquet...")
    df = pd.read_parquet(ARQUIVOS["municipios"])

    cols = [c for c in COLUNAS_MUNICIPIOS if c in df.columns]
    df = df[cols].copy()

    if "COD_MUNIC_IBGE" in df.columns:
        df["COD_MUNIC_IBGE"] = pd.to_numeric(df["COD_MUNIC_IBGE"], errors="coerce")

    print(f"  Linhas: {len(df)} | Colunas: {len(df.columns)}")

    # Converter para dicionário indexado por COD_MUNIC_IBGE (mais eficiente para lookup no JS)
    municipios = {}
    for _, row in df.iterrows():
        cod = row.get("COD_MUNIC_IBGE")
        if pd.isna(cod):
            continue
        municipios[int(cod)] = {k: (None if pd.isna(v) else v) for k, v in row.items() if k != "COD_MUNIC_IBGE"}

    salvar_json(municipios, os.path.join(PASTA_SAIDA, "municipios.json"))


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("Conversão Parquet → JSON — Painel de Entregas SDR")
    print("=" * 50)

    # Verificar arquivos de entrada
    for nome, arquivo in ARQUIVOS.items():
        if not os.path.exists(arquivo):
            print(f"\n❌ Arquivo não encontrado: {arquivo}")
            print("   Execute na pasta onde estão os Parquets.")
            exit(1)

    converter_agregado()
    converter_a_executar()
    converter_municipios()

    print("\n✅ Conversão concluída! Arquivos em:", PASTA_SAIDA)
    print("\nPróximos passos:")
    print("  1. Subir a pasta 'data/' para o GitHub")
    print("  2. Subir o index.html novo para o GitHub")
