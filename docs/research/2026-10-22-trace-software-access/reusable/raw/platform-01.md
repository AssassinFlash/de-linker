# https://intofuture.org/aladdin.html

# Aladdin — Institute for Future Intelligence

## What is Aladdin

Artificial intelligence is changing the way people think and work. As a manifestation of human ingenuity, design is a vital testbed for studying how we may meet the opportunities and challenges posed by AI. Based on the fusion of [CAD](https://en.wikipedia.org/wiki/Computer-aided_design), [CAE](https://en.wikipedia.org/wiki/Computer-aided_engineering), and [LLM](https://en.wikipedia.org/wiki/Large_language_model), Aladdin is an experimental platform for engineering design in the AI era, with a current focus on energy and civil engineering. a

Live model — [view fullscreen](https://intofuture.org/aladdin.html#). The Golden Gate Bridge.

## Design, simulation, and analysis

Aladdin is an integrated CAD/CAE platform that lets you design a structure and simulate its function _within a single system_. This eliminates complicated [toolchains](https://en.wikipedia.org/wiki/Toolchain) needed in traditional engineering design software and reduces the difficulty of implementing automatic design with AI.

### Building design

A building can be drawn wall by wall, or stated _parametrically_ — a footprint, a height, a storey count, a window-to-wall ratio for each facade — so that a whole block can be massed in minutes and still be handed to the same thermal engine as a hand-drawn house. Simulations are driven by real weather: an hourly [typical meteorological year](https://en.wikipedia.org/wiki/Typical_meteorological_year) for the site, so a design is tested against the climate it will actually stand in.

![Computational building-energy analysis with Aladdin](https://intofuture.org/image/aladdin-four-season-heatmap.png)

Computational building-energy analysis with Aladdin (see [more information](https://intofuture.org/aladdin-building-energy-2.html)).

Accuracy matters more than appearance in a tool meant for engineering, so Aladdin's building-energy simulation is checked against the [ASHRAE BESTEST benchmarks](https://intofuture.org/aladdin-bestest-validation.html), the standard suite of test cases for validating building-energy software.

### Solar power

Photovoltaic arrays can be laid out on roofs, facades, and open ground, with real module specifications, trackers that follow the sun, and bifacial panels that harvest the light reflected off the ground beneath them. [Concentrated solar power](https://en.wikipedia.org/wiki/Concentrated_solar_power) is here as well — heliostat fields around a power tower, parabolic troughs and dishes, and linear Fresnel reflectors — and each is simulated with the same solar-radiation engine that shades a window or heats a wall.

![Photovoltaic solar design with Aladdin](https://intofuture.org/image/aladdin-pv-design.png)

Photovoltaic solar design with Aladdin (see [more examples](https://intofuture.org/aladdin-pv.html)).

### Wind power

A wind farm can be built from real machines or from imagined ones. Every turbine carries a _power curve_ — the relationship between wind speed and electric output — which may be the manufacturer's, read straight off a datasheet by Aladdin, or one you invent for a rotor that does not exist yet. The wind itself comes from the site's typical meteorological year: an hourly record of speed and direction, gathered into a wind rose that shows where the year's energy actually blows from.

Yield is computed turbine by turbine across the year, with wakes accounted for — a rotor standing downstream of another meets slower air and earns less — so the farm's capacity factor depends on how the machines are arranged and not merely on how many there are. The terrain counts too: elevation data is fetched for the site, so the turbines stand on the real hills rather than on a flat abstraction of them.

![Wind rose for a wind farm site in Aladdin](https://intofuture.org/image/aladdin-wind-turbines-on-hills-windrose.png)

The wind rose of a site, drawn from hourly weather records (see [the power in the hills](https://intofuture.org/aladdin-wind-turbines-on-hills.html)).

A wind farm is more than its yield, however, and Aladdin also maps what the neighbors will ask about: the noise it radiates and the shadow flicker its blades cast. And the layout itself can be searched rather than guessed — a genetic algorithm moves the turbines within the site boundary, weighing wake losses against the wind resource until it finds an arrangement that harvests more than the one you drew by hand.

### Bridge design

A bridge is assembled as a three-dimensional frame of deck, towers, cables, and piers, and solved with [finite element analysis](https://en.wikipedia.org/wiki/Finite_element_method). A static analysis reports the deflection under dead and traffic loads, the axial force and bending moment in every member, and how close each member runs to its capacity. A modal analysis extracts the natural frequencies and mode shapes — the ways the structure prefers to move.

![Vibration modes of a bridge computed in Aladdin](https://intofuture.org/image/aladdin-bridge-design-modes.gif)

The vibration modes of a bridge (see [the bridge that bends](https://intofuture.org/aladdin-bridge-design.html)).

From there the questions get harder. A seismic analysis shakes the structure, either against a design response spectrum or with a recorded ground motion such as El Centro. A wind analysis hunts for the speed at which the deck starts to shed vortices or to flutter — the mechanism that tore down the Tacoma Narrows Bridge. And a pushover analysis raises the load until members yield one after another and the structure comes down, a collapse you can replay to see which member went first. An optimizer can then search the design space for the cheapest structure that still keeps deflection and member utilization inside their limits.

## Artificial intelligence

Aladdin's intelligence comes in two forms: an assistant that designs alongside you, and an evolutionary search that designs on its own.

### The AI assistant

All of this is also available to an AI assistant that lives inside the application and works the software the way a person does. Ask it for a house with dormers and a front porch and it builds the thing element by element while you watch. Ask what the house would cost to heat and it runs the simulation and reads the answer back. Ask it to align the dormer ridges with the roof, to add a chimney, to tilt the panels toward the winter sun, to test the bridge in an earthquake, or to optimize the wind farm's layout, and it reaches for the same tools you would.

It is not a chatbot bolted to the side of the program. It reads the live scene — including the change you just made by hand — and when a question is better answered by showing than by telling, it can open the very dialog you would have opened yourself, which makes it a tutor as much as a builder. Its purpose is not to take the design away from the designer but to remove the tedium between having an idea and seeing whether it works.

![Architectural design with Aladdin](https://intofuture.org/image/aladdin-building-design.png)

Architectural design with Aladdin (see [more examples](https://intofuture.org/aladdin-building-energy.html)).

### Generative design

Aladdin's other AI capability is agentic generative design, a _tabula rasa_ methodology inspired by biological evolution. Once the design criteria and constraints of a product are specified, generative design uses evolutionary computation to efficiently explore the entire parameter space supported by the software to find optimal solutions.

During the iterative search, the software automatically constructs a vast number of forms at each step, tests their functions with numerical simulations, evaluates their quality against the given criteria, and selects those closer to the goal for the next step. By repeating these routines many times, a variety of designs that meet the goal gradually emerge. Engineers then review these outputs — often with the aid of [interactive visual analytics](https://intofuture.org/aladdin-generative-design-1.html) for intuitive evaluation and comparison — and choose one or more for prototyping. This paradigm shift entails a fundamental change of mindset for [design thinking](https://en.wikipedia.org/wiki/Design_thinking) that must be addressed in the engineering education of the future workforce.

## How to cite Aladdin

Charles Xie, Xiaotong Ding, & Rundong Jiang, [Using Computer Graphics to Make Science Visible in Engineering Education](https://ieeexplore.ieee.org/document/10251686), _IEEE Computer Graphics and Applications_, 43(5), 99–106, 2023. DOI:10.1109/MCG.2023.3298386
