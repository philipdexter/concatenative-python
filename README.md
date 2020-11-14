
# Concatenative Python

Inspiration taken mostly from [Factor](https://factorcode.org/).

Write intuitive code like the following!

```python

num_unique = (lambda x: (push(x) >>
                         wdotc('split') >>
                         mk(lambda x: set(x)) >>
                         mk(len))())
def test_num_unique():
  assert num_unique('the second largest ocean is the second largest ocean') == (5,)

word_count = (lambda x: (push(x) >>
                         wdotc('split') >>
                         push(dd) >>
                         quot(inc_elem) >>
                         iter >>
                         mk(lambda x: dict(x)))())
def test_word_count():
  assert word_count('the second largest ocean is the second largest ocean') == ({'the': 2, 'second': 2, 'largest': 2, 'ocean': 2, 'is': 1},)
```
