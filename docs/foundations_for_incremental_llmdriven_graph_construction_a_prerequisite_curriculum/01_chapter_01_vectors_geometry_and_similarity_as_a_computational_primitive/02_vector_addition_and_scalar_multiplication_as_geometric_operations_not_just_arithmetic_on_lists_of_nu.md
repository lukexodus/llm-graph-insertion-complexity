## Vector Addition and Scalar Multiplication as Geometric Operations, Not Just Arithmetic on Lists of Numbers

### Two Views of the Same Operation

A `JOIN` between two tables can be described in two ways: as a formal relational-algebra operation on sets of tuples, or as a physical nested-loop or hash-based procedure the query planner actually runs. Both descriptions are correct, and neither is "the real one" — the algebraic description tells you *what* the result means, and the procedural one tells you *how* it's computed.

Vector addition and scalar multiplication have exactly this same split personality. Componentwise, they're nothing but arithmetic: add corresponding numbers, or multiply every number by a constant. Geometrically, they're operations on arrows in space: chaining displacements together, or stretching and flipping them. Recall that a vector can be understood as a point, an arrow, or a coordinate tuple, and that fixing an origin makes these views interchangeable — the arithmetic view of addition and scaling corresponds exactly to the coordinate-tuple model, while the geometric view corresponds to the arrow model. This item's whole point is that the two are not merely compatible, they are *identical* — the arithmetic is not an approximation of the geometry, and the geometry is not a metaphor for the arithmetic.

### Vector Addition, Arithmetically

Given two vectors as coordinate tuples, addition is defined componentwise — combine the corresponding fields, the same way you'd merge two structurally identical `struct`s field by field:

$$u + v = (u_1 + v_1,\ u_2 + v_2,\ \ldots,\ u_n + v_n)$$

For a concrete case, take $u = (2, 1)$ and $v = (1, 3)$ in two dimensions:

$$u + v = (2+1,\ 1+3) = (3, 4)$$

There is nothing here beyond elementwise addition of two arrays. But that flatness is exactly why the geometric picture matters: it tells you *what this elementwise sum represents*, which the arithmetic alone doesn't reveal.

### Vector Addition, Geometrically: Chaining Displacements

Recall that an arrow vector represents a displacement — a direction and a distance to travel — and that it is a **free vector**, meaning it represents the same displacement no matter where its tail is placed. Vector addition, geometrically, is what happens when you perform one displacement immediately followed by another: **place the tail of the second arrow at the head of the first, and the sum is the single arrow from the start of the first to the end of the second.**

This is the same idea as composing two relative filesystem moves: "go up two directories, then over into `logs/`" is a single combined relative path, computed by concatenating the two moves — you don't need to know your absolute starting directory to compose them, and the combined move is well-defined regardless of where you start from.

Trace the example above step by step:

- Start at the origin $(0,0)$.
- Apply $u = (2,1)$: move 2 units along the first axis and 1 unit along the second axis, arriving at $(2,1)$.
- From there, apply $v = (1,3)$: move 1 more unit along the first axis and 3 more along the second, arriving at $(2+1,\ 1+3) = (3,4)$.
- The single arrow from the origin straight to $(3,4)$ is $u+v$.

This is the **head-to-tail rule**, sometimes called the **parallelogram rule** because if you also draw $v$ starting from the origin and $u$ starting from the head of $v$, the two chained paths and the two original arrows trace out a parallelogram, with $u+v$ as its diagonal.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 320">
<text x="10" y="18" font-size="13" fill="#333">Vector Addition: Head-to-Tail Chaining (svg_diagram)</text>
<line x1="40" y1="290" x2="400" y2="290" stroke="#888" stroke-width="1" />
<line x1="40" y1="290" x2="40" y2="30" stroke="#888" stroke-width="1" />
<text x="405" y="295" font-size="11" fill="#888">x</text>
<text x="30" y="25" font-size="11" fill="#888">y</text>
<circle cx="40" cy="290" r="3" fill="#333" />
<text x="15" y="308" font-size="11" fill="#333">O</text>
<line x1="40" y1="290" x2="120" y2="250" stroke="#1a73e8" stroke-width="2" marker-end="url(#ah1)" />
<text x="70" y="260" font-size="12" fill="#1a73e8">u (2,1)</text>
<line x1="120" y1="250" x2="160" y2="90" stroke="#188038" stroke-width="2" marker-end="url(#ah2)" />
<text x="130" y="170" font-size="12" fill="#188038">v (1,3)</text>
<line x1="40" y1="290" x2="156" y2="94" stroke="#d93025" stroke-width="2.5" stroke-dasharray="1,0" marker-end="url(#ah3)" />
<text x="165" y="120" font-size="12" fill="#d93025">u+v = (3,4)</text>
</svg>

### Vector Subtraction as a Special Case

Subtraction, $v - u$, is addition of $u$'s reverse: $v + (-u)$. Geometrically it answers a different but related question than addition does — not "what do you get by chaining two displacements" but "what single displacement gets you from the tip of $u$ to the tip of $v$." This is exactly the arrow-between-two-points construction: if $u$ and $v$ are treated as points, $v-u$ is the arrow pointing from $u$ to $v$. That construction becomes central once similarity metrics enter later items, because "how different are two embeddings" is fundamentally a question about the arrow between them.

### Scalar Multiplication, Arithmetically

Scalar multiplication takes one vector and one plain number (a **scalar** — an ordinary single number, as opposed to a vector, so called because it *scales* things) and multiplies every component by it:

$$c \cdot v = (c v_1,\ c v_2,\ \ldots,\ c v_n)$$

For $v = (2, 1)$ and $c = 3$: $3v = (6, 3)$. For $c = -1$: $-v = (-2,-1)$. For $c = 0.5$: $0.5v = (1, 0.5)$.

### Scalar Multiplication, Geometrically: Stretching and Flipping

Recall that an arrow's two defining properties are its **direction** and its **magnitude** (length), with magnitude for a 2D vector computed as $\|v\| = \sqrt{v_1^2+v_2^2}$. Scalar multiplication acts on exactly these two properties in a clean, separable way:

- **Magnitude** scales by the absolute value of $c$: $\|cv\| = |c| \cdot \|v\|$.
- **Direction** is either preserved (if $c > 0$) or exactly reversed (if $c < 0$), and is undefined only in the degenerate case $c=0$, which collapses the arrow to a single point at the origin.

So $3v$ points the same way as $v$ but is three times as long; $0.5v$ points the same way but is half as long; $-v$ points exactly opposite $v$ with the same length. This is analogous to a network QoS system scaling a bandwidth-allocation vector up or down under load: the *proportions between components* — the direction — stay fixed, while the *overall magnitude* changes uniformly.

Worked check using $v = (2,1)$, $\|v\| = \sqrt{4+1} = \sqrt5$, and $c=3$: $3v = (6,3)$, and $\|3v\| = \sqrt{36+9} = \sqrt{45} = 3\sqrt5$, confirming $\|3v\| = |3|\cdot\|v\|$.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 300">
<text x="10" y="18" font-size="13" fill="#333">Scalar Multiplication: Same Direction, Different Length (svg_diagram)</text>
<line x1="200" y1="270" x2="200" y2="30" stroke="#ccc" stroke-width="1" />
<line x1="40" y1="270" x2="400" y2="270" stroke="#ccc" stroke-width="1" />
<circle cx="200" cy="270" r="3" fill="#333" />
<text x="180" y="288" font-size="11" fill="#333">O</text>
<line x1="200" y1="270" x2="240" y2="230" stroke="#1a73e8" stroke-width="2" marker-end="url(#b1)" />
<text x="245" y="228" font-size="11" fill="#1a73e8">v (2,1)</text>
<line x1="200" y1="270" x2="320" y2="150" stroke="#188038" stroke-width="2" marker-end="url(#b2)" />
<text x="325" y="148" font-size="11" fill="#188038">3v (6,3)</text>
<line x1="200" y1="270" x2="160" y2="310" stroke="#d93025" stroke-width="2" marker-end="url(#b3)" />
<text x="100" y="325" font-size="11" fill="#d93025">-v (-2,-1)</text>
</svg>

### Why the Geometric View Is Not Optional Decoration

It would be a mistake to treat the arrow picture as a nice teaching aid that can be discarded once the componentwise formulas are memorized, because two properties central to later chapters are visible only, or at least most cleanly, from the geometric side:

- **Direction preservation under positive scaling** is exactly why "moving toward" or "moving away from" a target vector by a small amount is a meaningful, well-defined operation — a fact leaned on when later items discuss nudging an embedding, or interpolating between two embeddings.
- **The parallelogram/head-to-tail structure of addition** is what makes it sensible to talk about a vector as a **weighted combination** of others (e.g., $0.3u + 0.7v$) — a blend that is itself a valid point in the same space, sitting somewhere on the segment connecting $u$'s and $v$'s positions. This is the geometric fact underlying idea like averaging several embeddings together to get a "centroid" representation, which resurfaces when embeddings are discussed as black-box outputs in the next chapter.

None of this is visible if addition and scaling are treated purely as "the componentwise formulas that happen to be correct" — the componentwise formulas are correct precisely *because* they compute the chaining-of-displacements and stretching-of-arrows operations described here, not the other way around.

### A Combined Worked Example

Take $u = (4, 0)$, $v = (0, 3)$, and compute $w = 0.5u + v$.

Arithmetically: $0.5u = (2, 0)$, so $w = (2,0) + (0,3) = (2, 3)$.

Geometrically: $u$ points purely along the first axis with length 4; scaling it by $0.5$ shrinks it, without changing direction, to length 2 — an arrow $(2,0)$. Chaining that shrunk arrow head-to-tail with $v$ — which points purely along the second axis with length 3 — means: move 2 units along the first axis, then 3 more units along the second, landing at $(2,3)$. Both routes agree, as they must, since they describe the same operation viewed two ways.

**Key Points**

- Vector addition and scalar multiplication are single operations with two equivalent descriptions: componentwise arithmetic, and geometric manipulation of arrows.
- Addition = head-to-tail chaining of displacements (equivalently, the parallelogram rule); the sum is well-defined regardless of where the arrows are drawn, because arrows are free vectors.
- Subtraction $v-u$ geometrically produces the arrow pointing from $u$ to $v$ — a construction that reappears when reasoning about distance between embeddings.
- Scalar multiplication scales magnitude by $|c|$ and preserves direction for $c>0$, reverses it for $c<0$, and collapses the vector to the origin for $c=0$.
- Weighted combinations of vectors (e.g. $0.3u+0.7v$) are geometrically meaningful points "between" the originals — the basis for later ideas like averaging embeddings.

**Next Steps**

- The dot product as a measure of directional agreement between vectors, building directly on the addition/scaling operations here.
- Deriving cosine similarity from the dot product and vector norm.
- Weighted combinations (centroids) of embeddings as an operational tool once embeddings are introduced as black-box outputs.