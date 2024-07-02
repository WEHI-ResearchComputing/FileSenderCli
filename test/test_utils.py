from filesender.api import iter_files
from pathlib import Path
import tempfile

def test_iter_files():
    with tempfile.TemporaryDirectory() as _tempdir:
        tempdir = Path(_tempdir)
        top_level_file = tempdir / "top_level_file"
        top_level_file.touch()

        top_level_dir = (tempdir / "top_level_dir")
        top_level_dir.mkdir()

        nested_file = top_level_dir / "nested_file.txt"
        nested_file.touch()

        nested_dir = top_level_dir / "nested_dir/"
        nested_dir.mkdir()

        doubly_nested_file = nested_dir / "doubly_nested_file.csv"
        doubly_nested_file.touch()

        assert set(iter_files([top_level_dir, top_level_file])) == {("top_level_file", top_level_file), ("top_level_dir/nested_file.txt", nested_file), ("top_level_dir/nested_dir/doubly_nested_file.csv", doubly_nested_file)}
