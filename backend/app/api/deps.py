
f
r
o
m
 
f
a
s
t
a
p
i
 
i
m
p
o
r
t
 
H
T
T
P
E
x
c
e
p
t
i
o
n
,
 
H
e
a
d
e
r
,
 
D
e
p
e
n
d
s


i
m
p
o
r
t
 
j
w
t


f
r
o
m
 
t
y
p
i
n
g
 
i
m
p
o
r
t
 
O
p
t
i
o
n
a
l


f
r
o
m
 
a
p
p
.
c
o
n
f
i
g
 
i
m
p
o
r
t
 
g
e
t
_
s
e
t
t
i
n
g
s


i
m
p
o
r
t
 
l
o
g
g
i
n
g




l
o
g
g
e
r
 
=
 
l
o
g
g
i
n
g
.
g
e
t
L
o
g
g
e
r
(
_
_
n
a
m
e
_
_
)


s
e
t
t
i
n
g
s
 
=
 
g
e
t
_
s
e
t
t
i
n
g
s
(
)




d
e
f
 
g
e
t
_
c
u
r
r
e
n
t
_
t
r
a
d
e
r
_
i
d
(
a
u
t
h
o
r
i
z
a
t
i
o
n
:
 
s
t
r
 
=
 
H
e
a
d
e
r
(
N
o
n
e
)
)
 
-
>
 
s
t
r
:


 
 
 
 
i
f
 
n
o
t
 
a
u
t
h
o
r
i
z
a
t
i
o
n
:


 
 
 
 
 
 
 
 
r
a
i
s
e
 
H
T
T
P
E
x
c
e
p
t
i
o
n
(
s
t
a
t
u
s
_
c
o
d
e
=
4
0
1
,
 
d
e
t
a
i
l
=
"
M
i
s
s
i
n
g
 
A
u
t
h
o
r
i
z
a
t
i
o
n
 
h
e
a
d
e
r
"
)


 
 
 
 
i
f
 
n
o
t
 
a
u
t
h
o
r
i
z
a
t
i
o
n
.
s
t
a
r
t
s
w
i
t
h
(
"
B
e
a
r
e
r
 
"
)
:


 
 
 
 
 
 
 
 
r
a
i
s
e
 
H
T
T
P
E
x
c
e
p
t
i
o
n
(
s
t
a
t
u
s
_
c
o
d
e
=
4
0
1
,
 
d
e
t
a
i
l
=
"
I
n
v
a
l
i
d
 
t
o
k
e
n
 
f
o
r
m
a
t
"
)


 
 
 
 


 
 
 
 
t
o
k
e
n
 
=
 
a
u
t
h
o
r
i
z
a
t
i
o
n
.
r
e
p
l
a
c
e
(
"
B
e
a
r
e
r
 
"
,
 
"
"
)


 
 
 
 
t
r
y
:


 
 
 
 
 
 
 
 
p
a
y
l
o
a
d
 
=
 
j
w
t
.
d
e
c
o
d
e
(
t
o
k
e
n
,
 
s
e
t
t
i
n
g
s
.
j
w
t
_
s
e
c
r
e
t
,
 
a
l
g
o
r
i
t
h
m
s
=
[
"
H
S
2
5
6
"
]
)


 
 
 
 
 
 
 
 
t
r
a
d
e
r
_
i
d
 
=
 
p
a
y
l
o
a
d
.
g
e
t
(
"
s
u
b
"
)


 
 
 
 
 
 
 
 
i
f
 
n
o
t
 
t
r
a
d
e
r
_
i
d
:


 
 
 
 
 
 
 
 
 
 
 
 
r
a
i
s
e
 
H
T
T
P
E
x
c
e
p
t
i
o
n
(
s
t
a
t
u
s
_
c
o
d
e
=
4
0
1
,
 
d
e
t
a
i
l
=
"
I
n
v
a
l
i
d
 
t
o
k
e
n
 
p
a
y
l
o
a
d
"
)


 
 
 
 
 
 
 
 
r
e
t
u
r
n
 
t
r
a
d
e
r
_
i
d


 
 
 
 
e
x
c
e
p
t
 
j
w
t
.
E
x
p
i
r
e
d
S
i
g
n
a
t
u
r
e
E
r
r
o
r
:


 
 
 
 
 
 
 
 
r
a
i
s
e
 
H
T
T
P
E
x
c
e
p
t
i
o
n
(
s
t
a
t
u
s
_
c
o
d
e
=
4
0
1
,
 
d
e
t
a
i
l
=
"
T
o
k
e
n
 
h
a
s
 
e
x
p
i
r
e
d
"
)


 
 
 
 
e
x
c
e
p
t
 
j
w
t
.
P
y
J
W
T
E
r
r
o
r
:


 
 
 
 
 
 
 
 
r
a
i
s
e
 
H
T
T
P
E
x
c
e
p
t
i
o
n
(
s
t
a
t
u
s
_
c
o
d
e
=
4
0
1
,
 
d
e
t
a
i
l
=
"
I
n
v
a
l
i
d
 
t
o
k
e
n
"
)




d
e
f
 
v
e
r
i
f
y
_
t
r
a
d
e
r
_
a
c
c
e
s
s
(
t
r
a
d
e
r
_
i
d
:
 
s
t
r
,
 
c
u
r
r
e
n
t
_
t
r
a
d
e
r
_
i
d
:
 
s
t
r
 
=
 
D
e
p
e
n
d
s
(
g
e
t
_
c
u
r
r
e
n
t
_
t
r
a
d
e
r
_
i
d
)
)
 
-
>
 
s
t
r
:


 
 
 
 
i
f
 
t
r
a
d
e
r
_
i
d
 
!
=
 
c
u
r
r
e
n
t
_
t
r
a
d
e
r
_
i
d
:


 
 
 
 
 
 
 
 
l
o
g
g
e
r
.
w
a
r
n
i
n
g
(
f
"
A
c
c
e
s
s
 
d
e
n
i
e
d
:
 
u
s
e
r
 
{
c
u
r
r
e
n
t
_
t
r
a
d
e
r
_
i
d
}
 
t
r
i
e
d
 
t
o
 
a
c
c
e
s
s
 
t
r
a
d
e
r
 
{
t
r
a
d
e
r
_
i
d
}
"
)


 
 
 
 
 
 
 
 
r
a
i
s
e
 
H
T
T
P
E
x
c
e
p
t
i
o
n
(
s
t
a
t
u
s
_
c
o
d
e
=
4
0
3
,
 
d
e
t
a
i
l
=
"
N
o
t
 
a
u
t
h
o
r
i
z
e
d
 
t
o
 
a
c
c
e
s
s
 
t
h
i
s
 
t
r
a
d
e
r
'
s
 
d
a
t
a
"
)


 
 
 
 
r
e
t
u
r
n
 
t
r
a
d
e
r
_
i
d


