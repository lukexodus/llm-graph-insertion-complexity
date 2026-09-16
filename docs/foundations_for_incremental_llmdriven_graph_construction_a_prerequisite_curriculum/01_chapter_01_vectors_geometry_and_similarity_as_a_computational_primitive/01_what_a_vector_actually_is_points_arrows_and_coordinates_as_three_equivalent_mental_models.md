## What a Vector Actually Is: Points, Arrows, and Coordinates as Three Equivalent Mental Models

### Why One Mental Model Isn't Enough

In a relational database, a single row can be described in at least three ways that all pick out the same underlying fact: as a physical disk location (an address the storage engine can seek to), as a set of column values (`(id=7, price=19.99, qty=3)`), or as the *result* of applying an `UPDATE` delta to some previous row. None of these descriptions is "more true" than the others — they're three lenses on the same object, and which lens you reach for depends on what you're about to do with the row.

A vector works the same way. The same mathematical object can be described as a **point** (a location), an **arrow** (a displacement), or a **coordinate tuple** (an ordered list of numbers), and the entire reason this chapter opens with all three is that later chapters lean on whichever one is most convenient at the time. Similarity search leans on the "arrow" view. Storage and computation lean on the "coordinate tuple" view. Geometric intuition about where things sit leans on the "point" view. If you only ever hold one of these in your head, some later explanations will feel like they're talking about a different object than the one you learned.

### Model 1: The Point

The **point** model says a vector is a *location* in space — a specific spot, like a single cell in a spreadsheet grid or a specific memory address in a process's address space. Just as a memory address only means something relative to a fixed base (the start of the address space, or a segment base register), a point only means something relative to a fixed **origin** — an agreed-upon "zero" location that every point is measured from.

In two dimensions, a point is a spot on a flat plane, described by how far it sits along a horizontal axis and a vertical axis. In three dimensions, add a depth axis. The point model is the most static of the three: it doesn't inherently suggest movement or direction, just "here is a place."

### Model 2: The Arrow (Displacement)

The **arrow** model says a vector is a *displacement* — a movement from one location to another, carrying both a direction and a distance. This is the same idea as a `git diff`: it's not a snapshot of a file, it's the *delta* between two snapshots. An arrow vector doesn't ask "where am I," it asks "how far, and which way, did I move."

Because an arrow encodes only relative movement, not an absolute location, the *same* arrow can be drawn starting from anywhere in space and it still represents the same vector — this is the mathematical notion of a **free vector**: an arrow of a given length and direction is considered identical no matter where you place its tail, the same way a network routing delta of "3 hops east" describes the same relative move whether you start from router A or router B.

An arrow has two defining properties:

- **Direction** — which way it points.
- **Magnitude** (or length) — how far it goes. For a 2D arrow with horizontal and vertical extents $v_1$ and $v_2$, this is computed by ordinary Euclidean distance:

$$\|v\| = \sqrt{v_1^2 + v_2^2}$$

(In three dimensions this simply extends to $\sqrt{v_1^2 + v_2^2 + v_3^2}$.) This formula is just the Pythagorean theorem applied to the arrow's horizontal and vertical extents — nothing more exotic than that. This is the *only* piece of the "norm" idea this item needs; the deeper role that magnitude plays in similarity comparisons is developed fully in a later item of this chapter.

### Model 3: The Coordinate Tuple

The **coordinate tuple** model says a vector is simply an *ordered list of numbers* — exactly the way a `struct` in C or a fixed-schema row in a database is an ordered list of typed fields. A 3D vector as a coordinate tuple is written $(v_1, v_2, v_3)$, and nothing about this representation requires you to think about geometry at all — it's pure data, the same way a database engine doesn't need to think of a row as "a point in space" to store and retrieve it.

This is the representation that actually exists in a computer's memory: a vector embedding produced by a model, once it leaves the whiteboard and enters your program, *is* a coordinate tuple — typically a fixed-length array of floating-point numbers (`float32[384]`, for instance). Every operation you'll eventually run on embeddings — storing them, indexing them, computing distances between them — is, at the implementation level, an operation on coordinate tuples, even though you'll keep reasoning about them as points and arrows.

### Why All Three Are the Same Object

Here is the fact that ties the three models together, and it is the single most important idea in this item: **once you fix an origin, "the point $P$" and "the arrow from the origin to $P$" are the same vector, and the coordinates of that arrow are exactly the coordinates of that point.**

Concretely: if the origin is $O = (0,0)$ and a point sits at $P = (3, 2)$, then:

- As a **point**, it's the location three units along the horizontal axis and two units up.
- As an **arrow**, it's the displacement you'd travel to get from $O$ to $P$: three units right, two units up.
- As a **coordinate tuple**, it's simply the pair $(3, 2)$ — the same two numbers describing both the point's location and the arrow's horizontal/vertical extent.

Nothing computational changes between these three descriptions. What changes is which *question* the description makes easy to answer. "Is this point inside a bounding region?" is naturally a point question. "How far apart are two things, and in which direction?" is naturally an arrow question — you compute it by subtracting one point's coordinates from another's, which produces the arrow *between* them. "What do I pass to a function?" is naturally a coordinate-tuple question, because that's the form the data actually takes in memory.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 320">
<text x="10" y="18" font-size="13" fill="#333">Vector (3, 2): Point vs Arrow vs Coordinates (svg_diagram)</text>
<line x1="40" y1="280" x2="400" y2="280" stroke="#888" stroke-width="1" />
<line x1="40" y1="280" x2="40" y2="30" stroke="#888" stroke-width="1" />
<text x="405" y="285" font-size="11" fill="#888">x</text>
<text x="30" y="25" font-size="11" fill="#888">y</text>
<line x1="100" y1="275" x2="100" y2="285" stroke="#aaa" />
<line x1="160" y1="275" x2="160" y2="285" stroke="#aaa" />
<line x1="220" y1="275" x2="220" y2="285" stroke="#aaa" />
<line x1="35" y1="220" x2="45" y2="220" stroke="#aaa" />
<line x1="35" y1="160" x2="45" y2="160" stroke="#aaa" />
<circle cx="40" cy="280" r="3" fill="#333" />
<text x="10" y="298" font-size="11" fill="#333">O (0,0)</text>
<circle cx="220" cy="160" r="4" fill="#1a73e8" />
<text x="228" y="158" font-size="12" fill="#1a73e8">Point P (3, 2)</text>
<line x1="40" y1="280" x2="216" y2="163" stroke="#d93025" stroke-width="2" marker-end="url(#arrowhead)" />
<text x="90" y="240" font-size="12" fill="#d93025">Arrow O to P</text>
<text x="90" y="310" font-size="12" fill="#333">Coordinate tuple: (3, 2)</text>
</svg>

### A Worked Example: Same Vector, Three Descriptions

Take the 3D vector $v = (3, -1, 2)$.

- **As a point:** it is the location reached by moving 3 units along the first axis, $-1$ unit (i.e., one unit backward) along the second axis, and 2 units along the third axis, starting from a fixed origin $(0,0,0)$.
- **As an arrow:** it is a displacement — "3 forward, 1 back, 2 up" — and this displacement is the same vector no matter where in space you place its tail, because an arrow's identity is direction-and-length, not location.
- **As a coordinate tuple:** it is the ordered triple $(3, -1, 2)$, which in a program is stored exactly as you'd store any fixed-length numeric record — e.g. `[3.0, -1.0, 2.0]` as a `float32` array of length 3.

Its magnitude, using the extension of the earlier formula to three components, is:

$$\|v\| = \sqrt{3^2 + (-1)^2 + 2^2} = \sqrt{9 + 1 + 4} = \sqrt{14} \approx 3.742$$

Notice this computation only *needed* the coordinate-tuple view — you don't need to picture an arrow floating in space to compute $\sqrt{14}$. That's precisely the point of having three models: the geometric ones (point, arrow) build your intuition for *what a computation means*, while the coordinate-tuple model is what actually gets executed.

### A Note on What Stays Fixed and What Doesn't

One subtlety worth flagging now, because it resurfaces later: the **point** model depends on a chosen origin, and the **coordinate tuple** model depends on a chosen set of reference directions (a **basis** — informally, "which way counts as axis 1, which way counts as axis 2," analogous to choosing which column of a table means what). Change the origin or the basis, and the same physical vector gets *different numbers*. The **arrow** model is the most origin-independent of the three, since a free vector's identity (direction and length) doesn't care where you draw it.

This matters in practice because an embedding model implicitly fixes a basis and an origin when it produces vectors — you don't get to choose them, and you generally don't need to know what they "mean" geometrically. What you can rely on is that once an origin is fixed by the embedding model, treating each embedding as *both* a point and an arrow from that origin is consistent and safe, which is exactly why the two views are used interchangeably in later chapters.

**Key Points**

- A vector is one object with three equivalent descriptions: **point** (location, relative to an origin), **arrow** (displacement, direction + magnitude, origin-independent), and **coordinate tuple** (ordered list of numbers, the actual in-memory representation).
- Fixing an origin makes "the point $P$" and "the arrow from the origin to $P$" the same vector, with identical coordinates.
- The coordinate tuple is what a program actually manipulates; the point and arrow views exist purely to build correct intuition about what those manipulations mean.
- Magnitude (length) of an arrow generalizes the Pythagorean theorem: $\|v\| = \sqrt{v_1^2 + v_2^2 + \cdots}$.
- Points and coordinate tuples depend on a chosen origin/basis; arrows (as free vectors) do not.

**Next Steps**

- Dot product as a measure of directional agreement between two arrows.
- Deriving cosine similarity from the dot product and the norm.
- Euclidean distance versus cosine similarity versus raw dot-product similarity as three different questions about the same pair of vectors.
- How embedding models implicitly fix the origin and basis that later chapters treat as given.