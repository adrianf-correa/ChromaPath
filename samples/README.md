# Imagens de teste

Coloque nesta pasta as imagens usadas durante o desenvolvimento.

Os arquivos adicionados diretamente a `samples/` são ignorados pelo Git para
evitar publicar materiais sem licença de redistribuição.

A subpasta `fixtures/` contém somente imagens originais e redistribuíveis usadas
pelos testes automatizados. O par do robô apresenta o mesmo desenho em uma
versão limpa e outra com ruído controlado. O par `detached-details` acrescenta
três pequenos losangos legítimos separados do objeto principal para confirmar
que eles não sejam confundidos com resíduos.

As amostras determinísticas podem ser recriadas executando
`python tools/generate_fixtures.py`.
