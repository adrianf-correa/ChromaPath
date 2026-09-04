# ChromaPath

Vetorizador automático e adaptativo para converter logos, ícones, mascotes e
ilustrações raster em arquivos SVG.

O ChromaPath analisa cada imagem antes da conversão para reduzir ruídos,
variações de cor pouco relevantes e pequenas franjas indesejadas. A proposta é
oferecer um fluxo simples, sem exigir que o usuário escolha manualmente número
de cores, limiares ou parâmetros técnicos do vetorizador.

> **Status:** MVP funcional em desenvolvimento. O projeto já executa o pipeline
> completo de imagem raster para SVG.

## Principais recursos

- Entrada em PNG, JPG ou WEBP e saída em SVG.
- Correção automática da orientação EXIF.
- Preservação de transparência durante o processamento.
- Análise perceptual de cores no espaço CIELAB.
- Aplicação adaptativa de filtro bilateral para reduzir ruído sem suavizar toda
  a imagem indiscriminadamente.
- Limpeza conservadora de franjas transparentes.
- Normalização do interior de regiões quase pretas, preservando suas bordas.
- Escolha automática da remoção mínima de pequenos fragmentos.
- Simplificação adaptativa das cores finais sem impor uma paleta com tamanho
  fixo.
- Vetorização colorida utilizando o VTracer como backend.

## Instalação

O projeto requer Python 3.12 ou mais recente.

```powershell
git clone https://github.com/adrianf-correa/ChromaPath.git
cd ChromaPath
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Quando o ambiente virtual estiver ativo, o terminal exibirá `(.venv)` antes do
caminho atual.

## Uso

Execute o programa informando a imagem que deseja converter:

```powershell
python main.py "samples/minha-imagem.png"
```

O SVG será criado automaticamente em:

```text
outputs/minha-imagem.svg
```

Para escolher outro destino, utilize `--output` ou sua forma curta, `-o`:

```powershell
python main.py "samples/minha-imagem.png" --output "outputs/resultado.svg"
```

## Como funciona

```text
Imagem raster
    ↓
Leitura e normalização em RGBA
    ↓
Análise da transparência e das variações locais de cor
    ↓
Limpeza adaptativa de franjas e ruído
    ↓
Normalização protegida de regiões quase pretas
    ↓
Vetorização com VTracer
    ↓
Agrupamento perceptual dos preenchimentos
    ↓
SVG final
```

As decisões são tomadas a partir das características da própria imagem. Uma
arte com cores chapadas pode seguir sem filtro bilateral, enquanto uma imagem
com pequenas oscilações locais pode receber uma passagem conservadora. Dessa
forma, o programa não reduz todas as entradas ao mesmo número de cores.

## Ferramentas de desenvolvimento

Para gerar e medir lado a lado o VTracer direto e o pipeline completo:

```powershell
python -m src.comparison "samples/minha-imagem.png"
```

Os dois SVGs são armazenados em `outputs/comparisons/`, acompanhados no terminal
pela quantidade de caminhos, cores de preenchimento e tamanho de cada arquivo.

O analisador mostra as cores dominantes, suas frequências, distâncias
perceptuais, variações entre pixels vizinhos e informações de transparência:

```powershell
python -m src.color_analysis "samples/minha-imagem.png" --top 20
```

Para preservar o PNG intermediário e compará-lo com a entrada:

```powershell
python -m src.preprocess "samples/minha-imagem.png"
```

Esses comandos ajudam a investigar o pipeline. Para o uso comum, basta executar
`main.py`.

## Testes

O projeto utiliza o módulo `unittest`, incluído no Python:

```powershell
python -m unittest discover -s tests -v
```

Os testes verificam as principais decisões do pré-processamento, confirmam que
a simplificação das cores não modifica a quantidade de caminhos do SVG e usam
um par de imagens original para validar a remoção de ruído de ponta a ponta.

## Estrutura do projeto

```text
ChromaPath/
├── main.py                 # Entrada principal da aplicação
├── requirements.txt        # Dependências Python
├── docs/                   # Decisões e registros de experimentos
├── samples/                # Imagens locais usadas no desenvolvimento
├── outputs/                # Resultados gerados localmente
├── tests/                  # Testes automatizados
├── tools/                  # Geração reproduzível das amostras públicas
└── src/
    ├── color_analysis.py   # Diagnóstico e comparação de cores
    ├── preprocess.py       # Pré-processamento adaptativo
    ├── svg_postprocess.py  # Simplificação das cores do SVG
    └── vectorize.py        # Integração com o VTracer
```

As imagens locais usadas durante o desenvolvimento não são publicadas
automaticamente. Somente as amostras originais de `samples/fixtures/`, criadas
para os testes automatizados, fazem parte do repositório.

## Limitações atuais

- Fotografias não fazem parte do escopo principal do MVP.
- Imagens em que o desenho possui poucos pixels ainda podem produzir curvas e
  pontas imprecisas.
- Gradientes, brilhos e efeitos metálicos podem ser convertidos em faixas ou
  cores mais chapadas.
- Algumas decisões ainda utilizam limites experimentais que precisam ser
  validados com mais imagens.
- O projeto ainda não possui interface gráfica.

## Roadmap

- Validar e refinar a tolerância adaptativa com mais estilos de imagem.
- Melhorar a detecção de pequenas regiões sem remover detalhes relevantes.
- Comparar o backend atual com os novos recursos do VTracer 1.0.
- Ampliar o conjunto de imagens de teste com arquivos redistribuíveis.
- Criar uma interface simples para arrastar a imagem, visualizar e salvar o SVG.

O ponto de retomada e a sequência planejada estão no
[plano de próximas etapas](docs/next-steps.md).

## Registro de desenvolvimento

Os resultados, hipóteses e ajustes realizados com as imagens de teste estão no
[registro de experimentos](docs/experiments.md). Esse documento preserva o
processo de aprendizado sem transformar o README principal em um diário.

## Tecnologias

- Python
- Pillow
- NumPy
- OpenCV
- [VTracer](https://github.com/visioncortex/vtracer)

O ChromaPath utiliza o VTracer para gerar a geometria vetorial e desenvolve uma
camada própria de análise, pré-processamento e decisão automática ao redor dele.
