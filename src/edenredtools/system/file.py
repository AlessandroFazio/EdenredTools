class FileUtils:
    @staticmethod
    def ends_with_newline(path: str) -> bool:
        with open(path, 'rb') as f:
            f.seek(-1, 2)  # Seek to 1 byte before EOF
            last_byte = f.read(1)
            return last_byte == b'\n'