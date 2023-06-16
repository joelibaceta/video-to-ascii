<div align=center>

  ![Logo](./images/logo.svg)

<p>

  É um simples pacote de python para rodar videos no terminal usando caracteres [ASCII](https://en.wikipedia.org/wiki/ASCII).

  [![Contribuidores financeiros no Open Collective](https://opencollective.com/video-to-ascii/all/badge.svg?label=financial+contributors)](https://opencollective.com/video-to-ascii) [![PyPI version](https://badge.fury.io/py/video-to-ascii.svg)](https://badge.fury.io/py/video-to-ascii)
  [![Manutenibilidade](https://api.codeclimate.com/v1/badges/3108b26a0bcfffd4b4fe/maintainability)](https://codeclimate.com/github/joelibaceta/video-to-ascii/maintainability)
  [![constribuições bem-vindas](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/joelibaceta/video-to-ascii)

</p>

![Screenshot](./images/Simpsons.apng)

</div>

<details><summary><b>Traduções</b></summary>
<p>

- [🇺🇸 English](./README.md)
- [🇪🇸 Español](./translations/README_es.md)
- [🇹🇼 繁體中文](./translations/README_zh-TW.md)
- [pt-BR Português](./translations/README_pt-BR.md)

<p>
</details>

## Requisitos

- Python3
- PortAudio (_Necessário somente para instalação com suporte de áudio_)
- FFmpeg (_Necessário somente para instalação com suporte de áudio_)
- Linux ou MacOS ... por agora

## Instalação

Instalação padrão

```bash
$ pip3 install video-to-ascii
```

Instalação com suporte de áudio

```bash
$ pip3 install video-to-ascii --install-option="--with-audio"
```

## Como usar

Apenas execute `video-to-ascii` em seu terminal

```bash
$ video-to-ascii -f myvideo.mp4
```

### Opções

**`--strategy`**
Permite escolher a estratégia para renderizar a saída.

![Render Strategies](./images/Strategies.png)

**`-o --output`**
Exporta a saída renderizada para um arquivo bash para compartilhar com alguém.

![Exportando](./images/export.png)

**`-a --with-audio`**
Se foi feita a instalação com suporte de áudio, você pode usar essa opção para rodar a trilha de áudio enquanto o video renderiza os caracteres em ASCII.

## Como funciona

Todo video é composto por um número de frames que são executados em uma certa taxa de frames.

![Video Frames](./images/imgVideoFrames.png)

Uma vez que o terminal tem um número específico de linhas e colunas, nós temos que redimensionar o vídeo para ajustar as limitações da tela do terminal.

![Terminal](./images/imgTerminal.png)

Para chegar a uma visualização correta de todo o frame nós ajustamos a _altura do frame_ para igualar com as _linhas do terminal_, evitando de usar mais _caracteres_ que o número de _colunas do terminal_.

![Resizing](./images/imgResizing.png)

Quando um caractere é escolhido para representar um pixel nós temos que medir a relevância da cor desse pixel no frame, baseado nisso nós selecionamos o caractere mais apropriado baseado na [iluminação relativa](https://en.wikipedia.org/wiki/Relative_luminance) em espaços colorimétricos, usando a versão simplificada da função de luminosidade.

<p align="center">
  <img src="./images/Luminosity.svg">
</p>

> A luz verde contribui mais para a intensidade percebida pelos humanos, e a luz azul menos.

Essa função retorna um inteiro no intervalo entre 0 e 255, nós assinamos um caractere de acordo com a densidade para mostrar superfícies mais coloridas para áreas com maiores intensidades de cor (valores maiores).

```python
CHARS_LIGHT 	= [' ', ' ', '.', ':', '!', '+', '*', 'e', '$', '@', '8']
CHARS_COLOR 	= ['.', '*', 'e', 's', '@']
CHARS_FILLED    = ['░', '▒', '▓', '█']
```

O intervalo de cores reduzidas suportadas pelo terminal é um problema que precisamos levar em conta. Terminais modernos suportam até 256 cores, então nós precisamos encontrar a cor 8 bit mais próxima que se assemelha ao pixel original de cor 16 ou 24 bit, nós chamamos esse set de 256 cores de [cores ANSI](https://stackoverflow.com/questions/4842424/list-of-ansi-color-escape-sequences).

![The Mapping of RGB and ANSI Colors](./images/imgPixelSection.png)

![8 Bits Color Table](./images/8-bit_color_table.png)

Finalmente, quando colocamos isso tudo junto, nós temos um caractere apropriado para cada pixel e uma nova cor.

![Frame Image by Characters](./images/imgPixelImage.png)

## Contribuidores

### Contribuidores de código

Esse projeto existe graças as todas as pessoas que contribuíram. [[Contribua](./CONTRIBUTING.md)].

<a href="https://github.com/joelibaceta/video-to-ascii/graphs/contributors"><img src="https://opencollective.com/video-to-ascii/contributors.svg?width=890&button=false" /></a>

### Contribuidores Financeiros

Se torne um contribuidor financeiro e ajude a sustentar nossa comunidade. [[Contribua](https://opencollective.com/video-to-ascii/contribute/)].

Ou apenas me ajude [comprando um café](https://ko-fi.com/joelibaceta).

#### Individuos

<a href="https://opencollective.com/video-to-ascii#backers" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/individuals.svg?width=890"></a>

#### Organizações

Suporte esse projeto com a sua organização. Sua logo vai aparecer aqui com o link do seu website. [[Contribua](https://opencollective.com/video-to-ascii/contribute)]

<a href="https://opencollective.com/video-to-ascii/organization/0/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/0/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/1/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/1/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/2/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/2/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/3/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/3/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/4/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/4/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/5/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/5/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/6/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/6/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/7/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/7/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/8/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/8/avatar.svg"></a>
<a href="https://opencollective.com/video-to-ascii/organization/9/website" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/organization/9/avatar.svg"></a>

## Visto em
<a href="https://www.producthunt.com/posts/video-to-ascii" target="_blank" rel="noopener"><img src="https://user-images.githubusercontent.com/864790/124545434-a2e7fe80-ddee-11eb-9d80-f24049524fd9.png" width="100px"></a>
