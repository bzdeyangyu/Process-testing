from pathlib import Path
from tempfile import TemporaryDirectory

from pptx import Presentation

from generate_pptx import generate_pptx


def test_generate_pptx_creates_full_deck() -> None:
    with TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "deck.pptx"
        generate_pptx(output_path)
        presentation = Presentation(str(output_path))

    assert len(presentation.slides) >= 23
