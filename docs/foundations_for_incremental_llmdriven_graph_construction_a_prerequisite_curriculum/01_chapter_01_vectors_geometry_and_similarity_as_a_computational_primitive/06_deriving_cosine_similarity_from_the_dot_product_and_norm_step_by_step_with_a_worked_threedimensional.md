## Deriving Cosine Similarity from the Dot Product and Norm

### Setting the Scene: A Systems Analogy

Consider a simple network-monitoring scenario: for two hosts on a network, you build a vector describing how many bytes each host sent over each protocol in the last minute — say `(HTTP, DNS, SSH)` bytes. Host A might have sent a lot of everything (heavy traffic overall), while Host B sent very little of everything, but in the *same proportions*. Intuitively, these two hosts have the "same shape" of traffic profile even though their volumes differ wildly. A metric that captures "same shape, ignore total volume" is exactly what cosine similarity is built to compute. This is the geometric idea we now derive precisely: two vectors can point in *almost the same direction* regardless of how long they are.

### Recalling the Two Building Blocks

Before deriving the formula, recall the two ingredients it is built from.

Recall that the **dot product** of two vectors $\vec{a} = (a_1, a_2, \dots, a_n)$ and $\vec{b} = (b_1, b_2, \dots, b_n)$ is the sum of the products of their corresponding components:

$$\vec{a} \cdot \vec{b} = \sum_{i=1}^{n} a_i b_i$$

Recall that the **norm** (or magnitude, or length) of a vector $\vec{a}$ is the straight-line distance from the origin to the point it represents, computed as the square root of the dot product of the vector with itself:

$$\|\vec{a}\| = \sqrt{\vec{a} \cdot \vec{a}} = \sqrt{\sum_{i=1}^{n} a_i^2}$$

These two quantities are pure algebra — sums of products and square roots of sums of squares. Neither one, by itself, mentions an angle. The derivation below is the bridge that connects this algebra to the geometric idea of "angle between two vectors."

### The Law of Cosines as the Bridge

The cleanest way to connect the dot product to an angle is through the Law of Cosines, a standard trigonometric fact about triangles: for a triangle with sides of length $A$, $B$, and $C$, where $\theta$ is the angle between the sides of length $A$ and $B$:

$$C^2 = A^2 + B^2 - 2AB\cos\theta$$

Now place two vectors $\vec{a}$ and $\vec{b}$ tail-to-tail at the origin. They form two sides of a triangle, and the segment connecting their tips is the third side, represented by the vector $\vec{a} - \vec{b}$. Applying the Law of Cosines to this triangle, with $\theta$ as the angle between $\vec{a}$ and $\vec{b}$:

$$\|\vec{a} - \vec{b}\|^2 = \|\vec{a}\|^2 + \|\vec{b}\|^2 - 2\|\vec{a}\|\|\vec{b}\|\cos\theta$$

This is the geometric side of the bridge. Now we compute the same left-hand side algebraically, purely from the dot product definition, and the two expressions will meet in the middle.

### Expanding the Left Side Algebraically

Using the fact that $\|\vec{v}\|^2 = \vec{v} \cdot \vec{v}$ for any vector $\vec{v}$, and that the dot product distributes over subtraction just like ordinary multiplication:

$$\|\vec{a} - \vec{b}\|^2 = (\vec{a} - \vec{b}) \cdot (\vec{a} - \vec{b})$$

$$= \vec{a}\cdot\vec{a} - \vec{a}\cdot\vec{b} - \vec{b}\cdot\vec{a} + \vec{b}\cdot\vec{b}$$

Since the dot product is commutative ($\vec{a}\cdot\vec{b} = \vec{b}\cdot\vec{a}$), the two middle terms combine:

$$= \|\vec{a}\|^2 - 2(\vec{a}\cdot\vec{b}) + \|\vec{b}\|^2$$

### Setting the Two Expressions Equal

We now have two different derivations of the same quantity, $\|\vec{a}-\vec{b}\|^2$ — one purely geometric (Law of Cosines), one purely algebraic (dot product expansion). Setting them equal:

$$\|\vec{a}\|^2 - 2(\vec{a}\cdot\vec{b}) + \|\vec{b}\|^2 = \|\vec{a}\|^2 + \|\vec{b}\|^2 - 2\|\vec{a}\|\|\vec{b}\|\cos\theta$$

The $\|\vec{a}\|^2$ and $\|\vec{b}\|^2$ terms appear identically on both sides and cancel:

$$-2(\vec{a}\cdot\vec{b}) = -2\|\vec{a}\|\|\vec{b}\|\cos\theta$$

Dividing both sides by $-2$:

$$\vec{a}\cdot\vec{b} = \|\vec{a}\|\|\vec{b}\|\cos\theta$$

This single line is the entire payoff: it says the dot product, a purely algebraic quantity computed with no trigonometry at all, is secretly equal to the product of the two lengths times the cosine of the angle between them. Solving for $\cos\theta$ gives the definition of **cosine similarity**:

$$\cos\theta = \frac{\vec{a}\cdot\vec{b}}{\|\vec{a}\|\|\vec{b}\|}$$

### The Full Formula in Component Form

Substituting the component-wise definitions of the dot product and the norm gives the version you will actually compute in code:

$$\text{cosine\_similarity}(\vec{a}, \vec{b}) = \frac{\sum_{i=1}^{n} a_i b_i}{\sqrt{\sum_{i=1}^{n} a_i^2} \cdot \sqrt{\sum_{i=1}^{n} b_i^2}}$$

**Key Points**
- Cosine similarity is not a new primitive operation — it is the dot product *normalized* by the product of the two norms.
- Dividing by $\|\vec{a}\|\|\vec{b}\|$ is exactly what removes the influence of magnitude: scaling either vector by any positive constant leaves $\theta$, and therefore $\cos\theta$, unchanged. This is why it correctly captured the "same shape, different volume" traffic profiles in the opening analogy.
- The result is a single scalar between $-1$ and $1$: $1$ means the vectors point in exactly the same direction, $0$ means they are orthogonal (perpendicular), and $-1$ means they point in exactly opposite directions.
- The derivation used only the Law of Cosines and the algebraic distributive property of the dot product — no calculus, and nothing specific to two or three dimensions. The formula in component form is valid for a vector of any dimension $n$, which matters immediately once vectors have hundreds of components.

### Worked Three-Dimensional Example

Let $\vec{a} = (1, 2, 2)$ and $\vec{b} = (2, 0, 1)$.

**Step 1 — Compute the dot product.**

$$\vec{a}\cdot\vec{b} = (1)(2) + (2)(0) + (2)(1) = 2 + 0 + 2 = 4$$

**Step 2 — Compute the norm of $\vec{a}$.**

$$\|\vec{a}\| = \sqrt{1^2 + 2^2 + 2^2} = \sqrt{1+4+4} = \sqrt{9} = 3$$

**Step 3 — Compute the norm of $\vec{b}$.**

$$\|\vec{b}\| = \sqrt{2^2 + 0^2 + 1^2} = \sqrt{4+0+1} = \sqrt{5} \approx 2.236$$

**Step 4 — Divide the dot product by the product of the norms.**

$$\cos\theta = \frac{4}{3 \times 2.236} = \frac{4}{6.708} \approx 0.596$$

**Step 5 — Recover the angle, if needed.**

$$\theta = \arccos(0.596) \approx 53.4^\circ$$

**Output**
- $\vec{a}\cdot\vec{b} = 4$
- $\|\vec{a}\| = 3$
- $\|\vec{b}\| = \sqrt{5} \approx 2.236$
- Cosine similarity $\approx 0.596$
- Angle $\approx 53.4^\circ$

A cosine similarity of $0.596$ sits roughly in the middle of the $[-1, 1]$ range: the two vectors point in a broadly similar but far from identical direction — neither near-parallel (close to $1$) nor near-orthogonal (close to $0$). Note that this value is entirely independent of how long $\vec{a}$ and $\vec{b}$ happen to be: doubling $\vec{a}$ to $(2, 4, 4)$ would double the dot product to $8$ and double $\|\vec{a}\|$ to $6$, and the $2$'s cancel in the ratio, leaving $\cos\theta$ exactly unchanged.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 300">
  <text x="210" y="24" font-size="14" text-anchor="middle" fill="#222">Angle Between Two Vectors (svg_diagram)</text>
  <line x1="40" y1="260" x2="400" y2="260" stroke="#999" stroke-width="1" />
  <line x1="40" y1="260" x2="40" y2="40" stroke="#999" stroke-width="1" />
  <circle cx="40" cy="260" r="3" fill="#222" />
  <text x="26" y="278" font-size="12" fill="#222">O (origin)</text>
  <line x1="40" y1="260" x2="300" y2="90" stroke="#1a73e8" stroke-width="2" marker-end="url(#arrowA)" />
  <text x="308" y="86" font-size="13" fill="#1a73e8">a</text>
  <line x1="40" y1="260" x2="260" y2="200" stroke="#d93025" stroke-width="2" marker-end="url(#arrowB)" />
  <text x="268" y="204" font-size="13" fill="#d93025">b</text>
  <path d="M 95 244 A 55 55 0 0 0 112 205" fill="none" stroke="#555" stroke-width="1.5" />
  <text x="108" y="228" font-size="13" fill="#555">θ</text>
  <text x="210" y="295" font-size="13" text-anchor="middle" fill="#333">cos θ = (a · b) / (‖a‖ ‖b‖)</text>
</svg>

### Why This Derivation Matters Beyond Trigonometry

The step where $\|\vec{a}\|^2$ and $\|\vec{b}\|^2$ cancel out on both sides is not a coincidence of algebra — it is the entire reason cosine similarity is useful as a computational primitive. It guarantees, by construction rather than by empirical luck, that the metric measures *orientation* and is provably blind to *scale*. That guarantee is what will later justify treating cosine similarity as a stable notion of "semantic closeness" between vectors whose magnitudes are not meaningful on their own — a property that becomes important once vectors are produced by a learned embedding model rather than chosen by hand.

**Related Topics**
- Deriving the norm from the dot product and the Pythagorean theorem in two and three dimensions
- Euclidean distance versus cosine similarity versus raw dot-product similarity as three distinct notions of "closeness"
- Why cosine similarity is undefined for a zero vector, and how implementations guard against division by zero
- Extending the geometric intuition from three dimensions to high-dimensional embedding spaces
- The curse of dimensionality and its effect on the distribution of pairwise cosine similarities