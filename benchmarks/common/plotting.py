"""House style for the comparison figures.

One rule decides the colours: **a colour belongs to a code, not to a position in
a legend.** FISPACT-II is the same blue on every figure on the site, whether it
is the only line beside the measurement or one of four, so a reader who has
learned one plot can read the next without checking the legend again. Nothing
here is ever assigned by rank or cycled.

The measurement is not a series and does not take a hue. It is black points with
error bars, because it is the thing everything else is being judged against.

Figures are written twice, `<name>.png` and `<name>-dark.png`, stepped for each
surface rather than flipped. mkdocs-material picks between them from the
reader's theme with the `#only-light` / `#only-dark` image suffixes, so a dark
reader does not get a white rectangle burned into the page.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

# Two surfaces, and the same hues stepped for each. Validated as categorical
# palettes against both surfaces: worst adjacent CVD separation 9.2 (light) and
# 9.4 (dark) in OKLab x100, against a target of 8.
LIGHT = {
    "surface": "#fcfcfb",
    "text": "#0b0b0b",
    "muted": "#52514e",
    "grid": "#d8d7d2",
    "measurement": "#0b0b0b",
    "fispact": "#2a78d6",
    "yani": "#eb6834",
    "yani_best": "#1baf7a",
    "openmc": "#4a3aa7",
}

DARK = {
    "surface": "#1a1a19",
    "text": "#ffffff",
    "muted": "#c3c2b7",
    "grid": "#3d3c39",
    "measurement": "#ffffff",
    "fispact": "#3987e5",
    "yani": "#d95926",
    "yani_best": "#199e70",
    "openmc": "#9085e9",
}

MODES = [("", LIGHT), ("-dark", DARK)]

# Thin marks, recessive grid. The numbers behind every figure are also printed
# as a table on the same page, which is what discharges the relief rule for the
# one light-mode hue that sits below 3:1 against its surface.
LINE_WIDTH = 2.0
MARKER_SIZE = 5.0
GRID_ALPHA = 0.5


def style(axes, palette):
    """Recede everything that is not data."""
    axes.set_facecolor(palette["surface"])
    axes.grid(True, color=palette["grid"], alpha=GRID_ALPHA, linewidth=0.8)
    axes.set_axisbelow(True)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        axes.spines[spine].set_color(palette["grid"])
    axes.tick_params(colors=palette["muted"], labelsize=9)
    for label in (axes.xaxis.label, axes.yaxis.label):
        label.set_color(palette["text"])
        label.set_fontsize(10)


def save(figure, destination, palette):
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=150, facecolor=palette["surface"],
                   bbox_inches="tight")
    plt.close(figure)


def both_modes(draw, destination):
    """Render one figure twice, once per surface.

    `draw(palette)` returns a matplotlib figure. It is called once per mode
    rather than having its colours patched afterwards, because a legend, a
    fill and an errorbar all take their colours at construction.
    """
    destination = pathlib.Path(destination)
    written = []
    for suffix, palette in MODES:
        figure = draw(palette)
        path = destination.with_name(destination.stem + suffix + destination.suffix)
        save(figure, path, palette)
        written.append(path)
    return written


def image_markup(destination, alt):
    """The markdown that shows the right one of the pair per theme."""
    name = pathlib.Path(destination).name
    stem, _, extension = name.rpartition(".")
    return (f"![{alt}](figures/{stem}.{extension}#only-light)\n"
            f"![{alt}](figures/{stem}-dark.{extension}#only-dark)")
