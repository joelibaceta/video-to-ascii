<div align=center>

  ![Logo](../images/logo.svg)

<p>

  Es un paquete de Python simple para reproducir videos en una terminal usando caracteres [ASCII](https://en.wikipedia.org/wiki/ASCII).

  [![Financial Contributors on Open Collective](https://opencollective.com/video-to-ascii/all/badge.svg?label=financial+contributors)](https://opencollective.com/video-to-ascii) [![PyPI version](https://badge.fury.io/py/video-to-ascii.svg)](https://badge.fury.io/py/video-to-ascii)
  [![Maintainability](https://api.codeclimate.com/v1/badges/a5fcdf2b0cab41654ca3/maintainability)](https://codeclimate.com/github/joelibaceta/video-to-terminal/maintainability)
  [![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/joelibaceta/video-to-ascii)
  [![HitCount](http://hits.dwyl.io/joelibaceta/https://github.com/joelibaceta/video-to-ascii.svg)](http://hits.dwyl.io/joelibaceta/https://github.com/joelibaceta/video-to-ascii)

![screenshot](../images/Simpsons.apng)

</p>

</div>

<details><summary><b>Translations</b></summary>
<p>

- [🇺🇸 English](../README.md)
- [🇪🇸 Español](./README_es.md)
- [🇹🇼 繁體中文](./README_zh-TW.md)

<p>
</details>

## Requisitos

- Python3
- PortAudio (_Solo se requiere para la instalación con soporte de audio_)
- FFmpeg (_Solo se requiere para la instalación con soporte de audio_)

## Instalación

Instalación estándar

```bash
$ pip3 install video-to-ascii
```

Instalación con soporte de audio

```bash
$ pip3 install video-to-ascii --install-option="--with-audio"
```

## Cómo usarlo

Simplemente ejecute `video-to-ascii` en su terminal

```bash
$ video-to-ascii -f myvideo.mp4
```

### Opciones

**`--strategy`**
Permite elegir una estrategia para renderizar la salida.

![Render Strategies](./images/Strategies.png)

**`-o --output`**
Exporte la salida de renderizado a un archivo bash para compartir con alguien.

![Exporting](./images/export.png)

**`-a --with-audio`**
Si se realizó una instalación con soporte de audio, puede usar esta opción para reproducir la pista de audio mientras renderiza los caracteres ascii del video.

## Cómo funciona

Cada video está compuesto por un conjunto de fotogramas que se reproducen a una determinada velocidad de fotogramas.

![Video Frames](../images/imgVideoFrames.png)

Dado que un terminal tiene un número específico de filas y columnas, tenemos que cambiar el tamaño de nuestro video para ajustarlo a las limitaciones de tamaño del terminal.

![Terminal](../images/imgTerminal.png)

Para alcanzar una visualización correcta de un marco completo, necesitamos ajustar la _frame height_ para que coincida con las _terminal rows_, evitando usar más _caracteres_ que el número de _terminal columns_.

![Resizing](../images/imgResizing.png)

Al elegir un carácter para representar un píxel, necesitamos medir la relevancia del color de ese píxel en el marco, en base a eso podemos seleccionar el carácter más apropiado en función de la [luminancia relativa](https://en.wikipedia.org/wiki/Relative_luminance) en los espacios colorimétricos, usando una versión simplificada de la función de luminosidad .

<p align="center">
  <img src="../images/Luminosity.svg">
</p>

> La luz verde es la que más contribuye a la intensidad percibida por los humanos y la luz azul, la que menos.

Esta función devuelve un número entero en el rango de 0 a 255, asignamos un carácter según la densidad para mostrar la superficie más coloreada para las áreas con color más intenso (valores más altos).

```python
CHARS_LIGHT 	= [' ', ' ', '.', ':', '!', '+', '*', 'e', '$', '@', '8']
CHARS_COLOR 	= ['.', '*', 'e', 's', '@']
CHARS_FILLED    = ['░', '▒', '▓', '█']
```

La reducida gama de colores que admite el terminal es un problema que debemos tener en cuenta. Los terminales modernos admiten hasta 256 colores, por lo que necesitamos encontrar el color de 8 bits más cercano que coincida con el píxel original en color de 16 o 24 bits, a este conjunto de [colores ANSI](https://stackoverflow.com/questions/4842424/list-of-ansi-color-escape-sequences) de 256 colores lo llamamos.

![The Mapping of RGB and ANSI Colors](../images/imgPixelSection.png)

![8 Bits Color Table](../images/8-bit_color_table.png)

Finalmente, al ponerlo todo junto, tendremos un carácter apropiado para cada píxel y un nuevo color.

![Frame Image by Characters](../images/imgPixelImage.png)

## Contribuyentes

### Contribuyentes de Código

Este proyecto existe gracias a todas las personas que contribuyen. [[Contribute](../CONTRIBUTING.md)].

<a href="https://github.com/joelibaceta/video-to-ascii/graphs/contributors"><img src="https://opencollective.com/video-to-ascii/contributors.svg?width=890&button=false" /></a>

### Contribuyentes Financieros

Conviértete en un contribuyente financiero y ayúdanos a sostener nuestra comunidad.. [[Contribute](https://opencollective.com/video-to-ascii/contribute/)].

O tal vez sólo me [compre un café](https://ko-fi.com/joelibaceta).

#### Individuos

<a href="https://opencollective.com/video-to-ascii#backers" target="_blank" rel="noopener"><img src="https://opencollective.com/video-to-ascii/individuals.svg?width=890"></a>

#### Organizaciones

Apoye este proyecto con su organización. Su logotipo se mostrará aquí con un enlace a su sitio web. [[Contribute](https://opencollective.com/video-to-ascii/contribute)]

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

