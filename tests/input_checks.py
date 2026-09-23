"""Held editing keys keep selection, read-only and IME rules intact."""
import pygame
import saturn as ft


def check():
    field = ft.TextField('abcdef')
    backspace = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0)
    for _ in range(3):
        field._key(backspace)
    assert field.value == 'abc' and field._caret == 3
    field.read_only = True
    field._key(backspace)
    assert field.value == 'abc'
    field.read_only = False
    field._composition = '\u62fc'  # A CJK IME composition character.
    field._key(backspace)
    assert field.value == 'abc'
    field._composition = ''
    field._select_range(0, 2)
    field._key(backspace)
    assert field.value == 'c' and field._caret == 0
    field._key(backspace)
    assert field.value == 'c'


if __name__ == '__main__':
    check()
    print('HELD EDITING KEY CHECKS PASS')
