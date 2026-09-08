# Sonda interna do VTracer — somente pesquisa

**Não é um novo backend do ChromaPath. Os dois patches locais foram rejeitados.**
O produto continua usando o pacote Python `vtracer==0.6.15` sem modificações.
Ver a conclusão e as medidas em [experiments.md](../../docs/experiments.md).

## O que é reproduzido

- sdist Python 0.6.15: núcleo Rust `vtracer` 0.6.12;
- segmentação `visioncortex` 0.8.10 e todas as dependências transitivas do seu
  trecho do Cargo.lock original, incluindo versões/checksums;
- RGBA preparado pelo produto, spline, stacked, precisão de cor 5, quina 45,
  diferença de camadas 16, comprimento 4, 10 iterações, splice 45 e precisão de
  coordenadas `None`. `filter_speckle` continua vindo do pré-processamento;
- Rust compilado para WASI, executado pelo Node: não instala/substitui a extensão
  Python. O controle foi **igual byte por byte ao nativo nos 24 casos geométricos**.
  A comparação é com o retorno UTF-8 da API nativa, antes de a gravação em modo
  texto do Windows converter LF em CRLF.

A sonda usa as seis cores-chave determinísticas do original para transparência.
Se todas já existirem, falha explicitamente em vez de imitar seu fallback
aleatório. Não é uma implementação geral/substituta da API do VTracer.

`src/main.rs` serializa os caminhos e também salva o mapa de regiões **antes**
do ajuste de curvas. `visioncortex-0.8.10-experiment.patch` adiciona logs de merge
e dois candidatos independentes em `BuilderImpl::stage_2`. Sem variável de
candidato, só há observação; os critérios originais permanecem.

Os trechos derivados do VTracer e do visioncortex são acompanhados das respectivas
licenças MIT neste diretório. Arquivos completos, binários, compilador e imagens
ficam em `outputs/`, ignorado pelo Git; não versionar a árvore inteira da dependência.

## Preparação (opcional, não necessária para usar o ChromaPath)

Requer Python 3.12+, Git, Node e Sharp conforme `tools/package-lock.json`, Rust
1.90.0 com alvo `wasm32-wasip1`. Execute da raiz do repositório.

```powershell
python -m tools.backend_probe.prepare --alpha
```

Baixa somente arquivos oficiais fixados por SHA256 em `sources.json`. Não roda
instaladores nem instala pacotes Python. Recusa sobrescrever diretórios extraídos.
`--cache CAMINHO --offline --root OUTRO_DIRETORIO` permite conferir a extração e
a aplicação do patch a partir dos mesmos arquivos, sem rede. Esse modo foi testado:
fonte reconstruído idêntico após normalizar LF/CRLF.

Nesta sessão, Rust foi instalado **somente em outputs**, sem mudar PATH global.
Para repetir usando essa instalação já existente:

```powershell
$env:CARGO_HOME = (Join-Path (Get-Location) 'outputs/backend-investigation/cargo-home')
$env:RUSTUP_HOME = (Join-Path (Get-Location) 'outputs/backend-investigation/rustup-home')
$env:CARGO_TARGET_DIR = (Join-Path (Get-Location) 'outputs/backend-investigation/target')
& "$env:CARGO_HOME/bin/cargo.exe" build --manifest-path tools/backend_probe/Cargo.toml --target wasm32-wasip1 --release --locked
```

Em outra máquina, disponibilize Rust/alvo primeiro; o comando acima não instala
o compilador. A biblioteca Sharp pode ser preparada com `npm ci --prefix tools`.
Essas ferramentas são de desenvolvimento, não novas dependências de produção.

## Repetir o ensaio e observar os merges

Escolha uma pasta de saída nova para cada execução; os scripts não apagam ensaios.

```powershell
python -m tools.backend_experiment --node node --wasm outputs/backend-investigation/target/wasm32-wasip1/release/chromapath-backend-probe.wasm --output outputs/backend-investigation/geometry-repeat
```

Gera as 24 fixtures, verifica o controle nativo, executa os candidatos e mede
silhuetas, cores por região, ROIs, frestas e franja. `--seam-only` reduz a seis.
Nos casos seam, grava `control.jsonl`, `solid.jsonl`, `contact.jsonl`, SVGs,
mapas segmentados e rasterizações 4×. O pixel observado em 192px é `(20,40)`.

Para inspecionar só esse pixel, usando a entrada gerada:

```powershell
python -m tools.backend_probe.inspect --node node --wasm outputs/backend-investigation/target/wasm32-wasip1/release/chromapath-backend-probe.wasm --input outputs/backend-investigation/geometry-repeat/seam-192-phase0.5/input.rgba --size 192 192 --watch 7700 --output outputs/backend-investigation/watch-control
```

Adicionar `--patch solid-neighbour` ou `--patch boundary-contact` ativa **um** dos
candidatos rejeitados. `CHROMAPATH_PROBE_LOG` e `CHROMAPATH_WATCH` são internos ao
processo da sonda, não opções do produto.

## Versão nova em processo separado

A wheel fixa em `v1-python` é Windows x64 e fornece a API nova `Config`.
O ensaio usa os mesmos parâmetros quando equivalentes, desliga otimização e
simplificação novas e mantém o pós-processamento atual, sem retunar cores.
Watershed é uma segmentação diferente; seu `detail=128` não equivale a precisão 5.

```powershell
python -c "import sys; sys.path.insert(0,'outputs/backend-investigation/v1-python'); from pathlib import Path; from tools.backend_newversion import run; run(Path('outputs/backend-investigation/geometry-repeat'), Path('outputs/backend-investigation/alpha-repeat'), 'node')"
```

Não carregue as duas extensões na mesma sessão Python. Não faça `pip install`
da alpha no ambiente principal. O comando acima só altera o caminho de importação
daquele processo, sem modificar variáveis globais nem requirements.

## Teste específico, vermelho/verde

```powershell
python -m tools.check_backend_fringe outputs/backend-investigation/geometry-repeat/seam-192-phase0.5/control-final.png --size 192 --phase .5
python -m tools.check_backend_fringe outputs/backend-investigation/alpha-repeat/seam-192-phase0.5/watershed.png --size 192 --phase .5
```

O primeiro termina com código **1**, acusando 183,25 px² de coral externo; o
segundo termina com **0**. Não é um teste por contagem de paths/cores. Uma imagem
vazia ou sem uma das regiões principais também reprova. A métrica não aprova
silhueta, transparência nem cores: essas são regressões separadas, e a alpha
**não passou na aceitação ampla**. A suíte padrão testa o próprio detector sem
exigir Rust/Node, e não mascara o defeito atual como uma correção aprovada.

Os 12 casos anteriores podem ser repetidos com `tools.backend_regressions`:
`--baseline outputs/geometry-baseline-20260908/baseline.json --node node --output NOVA_PASTA`.
O modo controle exige igualdade dos 36 SVGs. Em um processo com a alpha carregada,
adicione `--control PASTA_DO_CONTROLE`: compara renders, cores e caminhos. Alguns
samples são locais/não públicos; não inventar ground truth vetorial para eles.
