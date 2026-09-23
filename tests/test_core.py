from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw

from fnf_optimizer.core import full_pipeline


def test_full_pipeline(tmp_path):
    source = tmp_path / "input"
    source.mkdir()

    image = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 2, 20, 28), fill=(255, 0, 0, 255))
    draw.rectangle((34, 4, 60, 26), fill=(0, 255, 0, 255))
    image.save(source / "test.png")

    (source / "test.xml").write_text(
        '''<?xml version="1.0" encoding="utf-8"?>
<TextureAtlas imagePath="test.png">
  <SubTexture name="red0000" x="0" y="0" width="32" height="32" frameX="0" frameY="0" frameWidth="32" frameHeight="32"/>
  <SubTexture name="green0000" x="32" y="0" width="32" height="32" frameX="0" frameY="0" frameWidth="32" frameHeight="32"/>
</TextureAtlas>''',
        encoding="utf-8",
    )

    output = tmp_path / "output"
    result = full_pipeline(str(source), str(output), factor=0.5, workers=2)

    assert result["extract"].processed == 2
    assert result["resize"].processed == 2
    assert result["generate"].processed == 1
    assert (output / "resized" / "Scala.txt").exists()
    assert (output / "sprites" / "test.png").exists()
    xml_path = output / "sprites" / "test.xml"
    assert xml_path.exists()
    assert len(ET.parse(xml_path).getroot().findall(".//SubTexture")) == 2
