from k_resdev_skill.io_utils import read_text_file


def test_read_text_file_supports_cp949(tmp_path):
    path = tmp_path / "plan-cp949.txt"
    path.write_bytes("과제명: AI 초음파 진단".encode("cp949"))

    assert read_text_file(path) == "과제명: AI 초음파 진단"
