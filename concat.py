"""
Concatenative programming (kinda) in Python

Inspiration mostly taken from Factor https://factorcode.org/
"""

from inspect import signature
from functools import wraps

class StackFunction:
  """
  The class exists to wrap functions so we can overload magic methods for functions
  """

  def __init__(self, f):
    self.f = f

  def __call__(self, *args, **kwargs):
    return self.f(*args, **kwargs)

  def __rshift__(self, other):
    # Pipe defined later on
    return Pipe(self, other)
  

def mk(f):
  # TODO handle kwargs somehow?
  num_params = len(signature(f).parameters)
  @wraps(f)
  def g(*args, **kwargs):
    split_at = len(args) - num_params
    to_keep, to_pass = args[:split_at], args[split_at:]
    r = f(*to_pass, **kwargs)
    if isinstance(r, (list, tuple)):
      return *to_keep, *r
    else:
      return *to_keep, r
  return StackFunction(g)

def test_mk():
  @mk
  def add(a, b): return a + b
  @mk
  def sub(a, b): return a - b

  stack = [1, 2, 3, 4, 5]

  assert add(*stack) == (1, 2, 3, 9)
  assert sub(*stack) == (1, 2, 3, -1)

@mk
def add(a, b): return a + b
@mk
def mul(a, b): return a * b
@mk
def sub(a, b): return a - b
@mk
def p(a): print(a)

# To work around syntax limitations, we create a push function
# to push literals to the stack
# TODO detect if push is passed a list, and if so wrap it in a new list when returning
push = lambda x: mk(lambda: x)

def test_push():
  stack = [1, 2, 3]
  assert push(1)(*stack) == (1, 2, 3, 1)

# When functions return multiple items to the stack they must
# return a list. When wanting to push a list, return a list of list

swap = mk(lambda a, b: (b, a))

def test_swap():
  stack = [1, 2, 3]
  assert swap(*stack) == (1, 3, 2)

def test_function_push_list():
  stack = [1, 2, 3]
  assert push([[1,2,3]])(*stack) == (1, 2, 3, [1, 2, 3])

# Pipe is a bad word, in reality this is just a stack
class Pipe:
  """A sequence of stack functions"""

  def __init__(self, *items):
    self.pipe = items

  def __call__(self, *stack):
    pipe_in = stack
    for item in self.pipe:
      pipe_in = item(*pipe_in)
    return pipe_in

  def __rshift__(self, other):
    self.pipe = list(self.pipe) # can't be a tuple if we use append or +=
    if isinstance(other, Pipe):
      self.pipe += other.pipe
      return self
    if isinstance(other, StackFunction):
      self.pipe.append(other)
      return self

def test_pipe():
  pipe = Pipe(add, add)
  stack = [1, 2, 3, 4]
  assert pipe(*stack) == (1, 9)

  pipe = add >> add
  stack = [1, 2, 3, 4]
  assert pipe(*stack) == (1, 9)

  pipe = push(1) >> push(2) >> add
  assert pipe() == (3,)

  pipe = push(1) >> push(2) >> push(3) >> add >> mul
  assert pipe() == (5,)

  pipe1 = push(1) >> push(2) >> push(3)
  pipe2 = add >> mul
  pipe = pipe1 >> pipe2
  assert pipe() == (5,)

# allow attr ('dot') access to stack items
def dot(attr_string):
  @mk
  def f(x):
    attr =  getattr(x, attr_string)
    # # another way to write this would be
    # pipe = push(x) >> push(attr_string) >> mk(lambda x, y: getattr(x, y))
    # attr = pipe()[0]
    if hasattr(attr, '__call__'):
      return mk(attr)
    else:
      return attr
  return f

# allow calling functions on the stack
@StackFunction
def call(*args, **kwargs):
  *rest, f = args
  return mk(f)(*rest)

# allow calling functions on the stack, and wrap result in a list
@StackFunction
def wcall(*args, **kwargs):
  *rest, f = args
  @wraps(f)
  def g(*args, **kwargs):
    return [f(*args, **kwargs)]
  return mk(g)(*rest)

def test_dot_call():
  pipe = push('hi there') >> dot('split') >> call
  assert pipe() == ('hi', 'there')

def test_dot_wcall():
  pipe = push('hi there') >> dot('split') >> wcall
  assert pipe() == (('hi', 'there'),)

dotc = lambda x: dot(x) >> call

def test_dotc():
  pipe = push('hi there') >> dotc('split')
  assert pipe() == ('hi', 'there')

wdotc = lambda x: dot(x) >> wcall

def test_dotc():
  pipe = push('hi there') >> wdotc('split')
  assert pipe() == (('hi', 'there'),)

# example: count the number of unique words in a string
num_unique = (lambda x: (push(x) >>
                         wdotc('split') >>
                         mk(lambda x: set(x)) >> # hack with lambda, since the way we detect num arguments doesn't work for 'set' for some reason
                         mk(len))())
def test_num_unique():
  assert num_unique('the second largest ocean is the second largest ocean') == (5,)

# pipes can be delayed using quot
# TODO quots are very limited
quot = push
def test_quot():
  delayed_pipe = push(1) >> push(2) >> push(3) >> add >> add
  pipe = quot(delayed_pipe) >> call
  assert pipe() == (6,)

# perform a quotation on ervery item in a list, building up a result
# quot must take two values and return one value
@mk
def iter(ll, start, q):
  for l in ll:
    start = q(l, start)[0]
  return start

def test_iter():
  assert (push([[1, 2, 3]]) >> push(0) >> quot(add) >> iter)() == (6,)

# example: count the number of unique words in a string
from collections import defaultdict
dd = defaultdict(lambda: 0)
@mk
def inc_elem(a, b):
  # TODO cheating a little bit here by using named args, should
  # really have some dups or something
  # could easily be written in concatenative-python using magic methods
  inc = mk(lambda x: x + 1)
  drop = mk(lambda x: [])
  # the following pipe corresponds to the code
  # b[a] += 1 ; return b
  pipe = (push(b) >> push(a) >> mk(lambda a, b: a.__getitem__(b)) >>
          inc >> push(b) >> push(a) >>
          mk(lambda a, b, c: b.__setitem__(c, a)) >> drop >> push(b))
  return pipe()
word_count = (lambda x: (push(x) >>
                         wdotc('split') >>
                         push(dd) >>
                         quot(inc_elem) >>
                         iter >>
                         mk(lambda x: dict(x)))())
def test_word_count():
  assert word_count('the second largest ocean is the second largest ocean') == ({'the': 2, 'second': 2, 'largest': 2, 'ocean': 2, 'is': 1},)
