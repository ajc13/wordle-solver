# solver


import string


from pathlib import Path


from collections import Counter
from itertools import chain


import operator


DICT = "5_letter_words"


ALLOWABLE_CHARACTERS = set(string.ascii_letters)
ALLOWED_ATTEMPTS = 6
WORD_LENGTH = 5


WORDS = {
    word.lower()
    for word in Path(DICT).read_text().splitlines()
    if len(word) == WORD_LENGTH and set(word) < ALLOWABLE_CHARACTERS
}


LETTER_COUNTER = Counter(chain.from_iterable(WORDS))


LETTER_FREQUENCY = {
    character: value / LETTER_COUNTER.total()
    for character, value in LETTER_COUNTER.items()
}




def calculate_word_commonality(word):
    score = 0.0
    for char in word:
        score += LETTER_FREQUENCY[char]
    return score / (WORD_LENGTH - len(set(word)) + 1)




def sort_by_word_commonality(words):
    sort_by = operator.itemgetter(1)
    return sorted(
        [(word, calculate_word_commonality(word)) for word in words],
        key=sort_by,
        reverse=True,
    )




def display_word_table(word_commonalities):
    for word, freq in word_commonalities:
        print(f"{word:<10} | {freq:<5.2}")




def input_word():
    while True:
        word = input("Input the word you entered> ")
        print(word, len(word), word.lower() in WORDS)
        if len(word) == WORD_LENGTH and word.lower() in WORDS:
            print(f"{word:<10} | {calculate_word_commonality(word):<5.2}") 
            break
    return word.lower()




def input_response():
    print("Type the color-coded reply from Wordle:")
    print("  G for Green")
    print("  Y for Yellow")
    print("  ? for Gray")
    while True:
        response = input("Response from Wordle> ")
        response = response.upper()
        if len(response) == WORD_LENGTH and set(response) <= {"G", "Y", "?"}:
            if response == "GGGGG":
                print("Seems you are done!")
                exit()
            else:
                break
        else:
            print(f"Error - invalid answer {response}")
    return response




def match_word_vector(word, word_vector):
    assert len(word) == len(word_vector)
    for letter, v_letter in zip(word, word_vector):
        if letter not in v_letter:
            return False
    return True




def match(word_vector, possible_words):
    return [word for word in possible_words if match_word_vector(word, word_vector)]




def solve():
    possible_words = WORDS.copy()
    word_vector = [set(string.ascii_lowercase) for _ in range(WORD_LENGTH)]
    for attempt in range(1, ALLOWED_ATTEMPTS + 1):
        print(f"Attempt {attempt} with {len(possible_words)} possible words")
        display_word_table(sort_by_word_commonality(possible_words)[:32])
        word = input_word()
        response = input_response()
        for idx, letter in enumerate(response):
            if letter == "G":
                word_vector[idx] = {word[idx]}
            elif letter == "Y":
                possible_words_Y = possible_words.copy()
                for possible_word in possible_words_Y:
                    if word[idx] not in possible_word:
                        possible_words.remove(possible_word)
                try:
                    word_vector[idx].remove(word[idx])
                except KeyError:
                    pass
            elif letter == "?":
                for vector in word_vector:
                    try:
                        vector.remove(word[idx])
                    except KeyError:
                        pass
        possible_words = match(word_vector, possible_words)
        print(word_vector)




solve()
