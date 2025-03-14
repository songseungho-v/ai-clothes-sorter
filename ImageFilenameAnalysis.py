import os
import re
from collections import Counter


def get_most_common_words(directory, top_n=10):
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    word_counter = Counter()

    # 디렉토리 내 파일명 가져오기
    for filename in os.listdir(directory):
        name, ext = os.path.splitext(filename)
        if ext.lower() in image_extensions:
            words = re.findall(r'\w+', name.lower())  # 단어 추출 (소문자로 변환)
            word_counter.update(words)

    # 가장 많이 나온 단어 출력
    return word_counter.most_common(top_n)


if __name__ == "__main__":
    directory = input("분석할 이미지 파일 폴더 경로를 입력하세요: ")
    if os.path.isdir(directory):
        common_words = get_most_common_words(directory, top_n=200)
        print("가장 많이 등장하는 단어들:")
        for word, count in common_words:
            print(f"{word}: {count}번")
    else:
        print("올바른 디렉토리를 입력하세요.")