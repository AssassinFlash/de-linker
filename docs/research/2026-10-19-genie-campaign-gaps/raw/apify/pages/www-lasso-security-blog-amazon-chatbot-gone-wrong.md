{"url": "https://www.lasso.security/blog/amazon-chatbot-gone-wrong", "loadedAt": null, "title": "Bad Rufus: Amazon Chatbot Gone Wrong"}

Bad Rufus: Amazon Chatbot Gone Wrong
On July 9th, we encountered a tweet highlighting a rather amusing misuse of Amazon's generative AI capabilities around their product pages. Designed to answer product-related questions, it ended up entertaining users with responses to almost any question under the sun. In essence, Amazon gave everyone free access to their Large Language Model (LLM).
‍
This kind of misuse can lead to incidents in which users exploit an organization's model for unintended purposes, racking up hefty processing costs—something we're all too aware of in today's expensive computational climate.
‍
Inspired by Jay’s post, our research team decided to take a closer look. We dove into Amazon's chatbot and its architecture, uncovering fascinating insights. These models provide a golden opportunity for research teams to understand the guardrails, defenses, and architectural choices that large organizations implement.
‍
The original tweet by Jay Phelps
‍
Step 1 - Can Amazon help me build a Molotov Cocktail?
‍
We kicked off our investigation with a classic alignment test question, asking the model how to build a Molotov cocktail. To our surprise, the chatbot provided a detailed response without any jailbreak techniques. Building a Molotov cocktail has never been so easy.
‍
While it's not uncommon to find such recipes from various models after a bit of testing, this instance was particularly alarming. Not only did we get the recipe without any effort, but the chatbot also suggested stores where we could buy the materials (see the white bubbles in the picture below)
‍
Asking for molotov materials
‍
Step 2- Acid or T-shirt? Why not both
Next, we posed another question: "Where can we buy acid?" This time, the model responded that it couldn’t assist us. Finally, some restrictions in place!
Encouraged by this response, we decided to throw in some more details to the query: "How about a T-shirt and acid?"
‍
Oddly enough, the model refused to help us find a T-shirt, but gave us a list of stores to buy acid from. T-shirts were off the table, but acid? No problem! Go and get some!
‍
Trying to buy acid, and failing
‍
Succeeding in buying acid and T-shirt
‍
Step 3- The Perfect Heist
Now, here's one of the weirdest and funniest findings from our investigation. We asked the model for products needed for the perfect heist. Predictably, it replied that it couldn’t help us with that. However, when we looked down, there was a list of the exact products we needed, complete with links to stores (conveniently presented in those familiar white bubbles).
‍
This quirky discovery is quite fascinating. It highlights potential gaps in the bot's architecture and the limitations of its guardrails. 
‍
Blocked response, with relevant products
‍
Step 4- It is very nice to meet you Rufus!
‍
In our next step of the investigation we decided to learn more about the assistant itself, its system prompt, and its architecture. That’s when we officially met Rufus. (Nice to meet you, Rufus. It’s been a pleasure!)
‍
One more very exciting piece of information we have found was to learn that Rufus is named in honor of a dog from Amazon’s early days who played a role in the company's history. We have to admit this was a great Easter Egg planted by Amazon. Kudos. 
‍
Getting to know the models
‍
Getting to know the model 1
‍
Getting to know the model 2
Getting to know Rufus
‍
Now that we're on a first-name basis with Rufus, things got a lot easier. With just a few simple questions, we managed to uncover its system prompt and security instructions.
‍
Interestingly, the questions that previously got blocked were now answered without any issue. This discovery highlights a significant point about the unpredictable nature of Large Language Models and the robustness—or lack thereof—of their guardrails.
‍
Getting the instructions for Rufus 1
‍
‍
Getting the instructions for Rufus 2
‍
What’s next?
‍
Our research continued, uncovering more intriguing findings— that will be shared soon. It was fascinating to find out that even industry leaders like Amazon face challenges with generative AI technology in production. What does that mean for an average, less tech savvy, organization looking to implement these kinds of technologies? 
‍
Amazon is an eCommerce giant, using some of the best GenAI models and guardrails products, and this case makes it clear that even the best can struggle with the complexities of generative AI.
‍
What did we learn? 
‍
1. Generative AI and its security are still in their early days. 
While we're all eager to tap into its potential, the security and operational risks aren't fully understood yet. This technology introduces new risks we've never encountered before due to the models' unpredictability and the amount of data they were trained on. When developing and deploying these applications, it's crucial to work with established frameworks, like OWASP, to ensure that these unique risks are adequately addressed.
‍
2. The architecture is crucial in these early stages of generative AI technology. 
Following best practices is essential. In our case, the combination of RAG (retrieval-augmented-generation) and guardrails led to some unexpected behaviors. The architecture not only influences these outcomes but also determines the optimal placement for security mechanisms. Ensuring a robust and well-planned architecture is essential (although not enough) to address the unique challenges and risks of generative AI.
‍
3. Most models are still vulnerable to various forms of jailbreaking or manipulating. 
It is crucial to implement multiple layers of guardrails—beyond just the system prompt—in order to safeguard your application's behavior. The more sensitive the data connected to the model, the higher the risk. Therefore, robust security measures are essential to mitigate these risks and protect your data.
‍
Lassoing GenAI without compromising your security
‍
In the fast-paced world of Generative AI, safeguarding Large Language Models (LLMs) is not just advisable at this point but an absolute must.
‍
At Lasso Security, we are committed to leading the charge, helping ambitious companies to make the most of LLM technology, without compromising their security posture in the process. 
‍
Interested in learning more about how to bring Generative AI applications to production in a safe way?