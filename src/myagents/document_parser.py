from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union, List
import fitz  # PyMuPDF
from .diagram_to_mermaid_converter import DiagramToMermaidConverter

PathLike = Union[str, Path]

@dataclass
class DocumentParser:
    design_as_text: str = field(default_factory=str)
    converter: Optional[DiagramToMermaidConverter] = None  # optional; stub if None

    # --- public API ---
    def get_design_as_text(self) -> str:
        return self.design_as_text

    def set_design_as_text(self, text: str) -> None:
        self.design_as_text = text

    def parse_folder(self, folder: PathLike) -> None:
        root = Path(folder).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Invalid folder: {root}")
        for file in root.iterdir():
            if file.is_file():
                self.parse_file(file)

    def parse_file(self, file: Path) -> None:
        suffix = file.suffix.lower()
        if suffix == ".pdf":
            self._parse_pdf(file)
        else:
            # placeholder for other types (txt/docx/images) — add later
            self.design_as_text += f"\n[FILE] {file.name}"

    # --- internals ---
    def _parse_pdf(self, file: Path) -> None:
        assets_dir = file.parent / f"{file.stem}_assets"
        assets_dir.mkdir(exist_ok=True)

        text_parts: List[str] = []
        image_blocks: List[str] = []

        try:
            with fitz.open(file) as doc:
                for page_idx, page in enumerate(doc, start=1):
                    txt = (page.get_text("text") or "").strip()
                    if txt:
                        text_parts.append(f"\n\n# [PDF:{file.name}] Page {page_idx}\n{txt}")

                    for img_idx, img in enumerate(page.get_images(full=True), start=1):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        try:
                            if pix.alpha or pix.n > 3:
                                pix = fitz.Pixmap(fitz.csRGB, pix)
                            out_png = assets_dir / f"{file.stem}_p{page_idx}_i{img_idx}.png"
                            pix.save(out_png.as_posix())
                        finally:
                            pix = None

                        mermaid = self._image_to_mermaid(out_png)
                        image_blocks.append(
                            f"\n\n# [IMAGE:{file.name}] Page {page_idx} Image {img_idx}\n"
                            f"```mermaid\n{mermaid}\n```"
                        )
        except Exception as e:
            self.design_as_text += f"\n[PDF ERROR] {file.name}: {e.__class__.__name__}: {e}"
            return

        if text_parts:
            self.design_as_text += "".join(text_parts)
        if image_blocks:
            self.design_as_text += "".join(image_blocks)

    def _image_to_mermaid(self, image_path: Path) -> str:
        if not self.converter:
            return (
                f"%% TODO: Convert diagram at {image_path} to Mermaid\n"
                f"flowchart TD\nA[Image: {image_path.name}] --> B[Conversion pending]"
            )
        out_mmd = image_path.with_suffix(".mmd")
        try:
            mermaid = self.converter.convert(image_path=image_path, output_path=out_mmd)
            return (mermaid or "flowchart TD\nA --> B").strip()
        except Exception as e:
            return f"%% Conversion error {e.__class__.__name__}: {e}\nflowchart TD\nA --> B"
