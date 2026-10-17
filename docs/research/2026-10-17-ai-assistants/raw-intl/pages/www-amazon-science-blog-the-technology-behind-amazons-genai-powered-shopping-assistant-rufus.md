<!-- source: https://www.amazon.science/blog/the-technology-behind-amazons-genai-powered-shopping-assistant-rufus
     loadedTime(UTC): 2026-10-17T05:30:31.903Z
     httpStatus: 200
     apifyRun: TrRwuJPIOXuAAY33r (wcc-known-1) -->

# The technology behind Amazon’s GenAI-powered shopping assistant, Rufus

_\[Editor's note: A_ [_condensed version of this blog post_](https://spectrum.ieee.org/amazon-rufus) _appeared previously in_ IEEE Spectrum_\]_

"What do I need for cold-weather golf?”

“What are the differences between trail shoes and running shoes?”

“What are the best dinosaur toys for a five-year-old?”

These are some of the open-ended questions customers might ask a helpful sales associate in a brick-and-mortar store. But what about shopping online? How do customers navigate online selection?

A sample interaction with Rufus.

The answer for Amazon is Rufus, a generative-AI-powered shopping assistant. Rufus helps Amazon customers make more-informed shopping decisions by answering a wide range of questions in the Amazon Shopping app, from product details and comparisons to recommendations. And it exists because of advances and innovations in AI.

My team leads the scientific and engineering effort behind Rufus. To build a helpful conversational shopping assistant, it was critical to use innovative technologies across multiple aspects of generative AI. This included building a custom large language model (LLM) specialized for shopping; employing retrieval-augmented generation (RAG) with a variety of evidence sources; leveraging reinforcement learning to improve responses; making advances in high-performance computing to improve inference efficiency and reduce latency; and implementing a new streaming architecture to support a better customer experience. We selected AWS infrastructure, including the AWS chips Trainium and Inferentia, to deliver these experiences at scale because AWS offers the most advanced, secure, reliable, and price-performant generative-AI foundations.  

## 

Building a custom LLM from scratch

Most LLMs are trained on datasets that improve their overall knowledge and capabilities, and then they are customized for a particular domain. From the beginning, our aim with Rufus was to train it primarily with shopping data — the entire Amazon catalogue, for starters, as well as customer reviews and information from community Q&A posts. Our scientists built an advanced, custom LLM that incorporated these data sources along with public information on the web, carefully curating the contribution of each data source for model training. We used the AWS service Amazon EMR — a cloud big-data platform for doing large-scale distributed data processing — to prepare the data and Amazon S3, the leading cloud storage solution, to store the data. Both services played a pivotal role in creating a secure and reliable foundation to build the custom model.  

## 

Using RAG to surface well-sourced answers

To answer the vast span of questions that could possibly be asked, Rufus needs to be able to go beyond the training data and use information it hasn’t seen before. That’s where RAG comes in: before generating a response, the LLM first selects information that may be helpful in answering the shopper’s questions.

 [](https://www.amazon.science/blog/automated-evaluation-of-rag-pipelines-with-exam-generation)

Related content

The fight against hallucination in retrieval-augmented-generation models starts with a method for accurately assessing it.

But how does it know which information to choose? Rufus pulls information from sources it knows to be reliable, such as customer reviews, the product catalogue, and community questions and answers, along with calling relevant Stores APIs. The complexity of our RAG process is unique, both because of the variety of our data sources and the differing relevance of each one, depending on the question.  

## 

Constantly improving through reinforcement learning

Every LLM, and every use of generative AI, is a work in progress. For Rufus to become more helpful over time, it needs to learn which responses are helpful and which can be improved. Through a process called reinforcement learning, customers can be the best source of that information. Amazon encourages customers to give Rufus feedback, letting the model know if they liked or disliked answers. Over time, Rufus learns from customer feedback and improves its responses, generating answers that better help customers shop.  

## 

Low latency and high throughput with Amazon’s AI chips

Rufus needs to be able to engage with millions of customers simultaneously without any noticeable delay. This is particularly challenging since generative-AI applications are very computationally intensive, especially at Amazon’s scale.

 [](https://www.amazon.science/blog/using-teacher-knowledge-at-inference-time-to-enhance-student-model)

Related content

New method improves the state of the art in knowledge distillation by leveraging a knowledge base of teacher predictions.

To minimize latency while maximizing throughput, we turned to Amazon’s Trainium and Inferentia chips, which are integrated with core AWS services. We collaborated with the Neuron compiler team to implement optimizations that improve model inference efficiency, and we’ve made those optimizations available to all AWS customers. Choosing Amazon’s homegrown AI chips allowed our team to move quickly, deploy at scale, and keep pace with customer demand.

With LLMs, however, throughput and latency can still be compromised by standard methods for processing requests in batches. That’s because it’s difficult to predict how many tokens (in this case, units of text, such as words or punctuation marks) an LLM will generate as it composes a response. Our scientists worked with AWS to enable Rufus to use continuous batching, a novel LLM inference-specific technique that makes routing decisions for new requests after every token is generated. This enables the model to start serving new requests as soon as the first request in the batch finishes, rather than waiting for all the requests to finish, so shoppers get their answers faster.  

## 

Streaming architecture

We want Rufus to provide the most relevant and helpful answer to any given question. Sometimes that’s a long-form text answer, but sometimes it’s short-form text, or a clickable link that helps the customer navigate the store.

Presenting the answer in a way that’s easy for the customer to interpret presents its own technical difficulties. The information needs to follow a logical flow. If we didn’t group and format things correctly, we could end up with a confusing response that’s not very helpful.

 [](https://www.amazon.science/blog/new-contrastive-learning-methods-for-better-data-representation)

Related content

New loss functions enable better approximation of the optimal loss and more-useful representations of multimodal data.

With an advanced streaming architecture, Rufus is able to provide a natural customer experience. End-to-end streaming on a token-by-token basis means that customers don’t need to wait for a long answer to be fully generated. Instead, they get the first part of the answer while the rest is still in progress. Rufus will populate the streaming response with the right data — a process called hydration — by making queries to internal systems. It is trained to generate markup instructions that specify how various answer elements should be displayed, in addition to answering the customer question, resulting in a uniquely useful experience for the customer.

Even though Amazon has been using AI for more than 25 years to improve the customer experience, generative AI represents something new and transformative—for Amazon, its customers, and those of us on science teams that get to build experiences beyond what we thought were possible. We are excited to accelerate our pace of innovation for customers with generative AI and believe it will transform every customer experience in the months and years to come.

Trishul Chilimbi is a vice president and distinguished scientist with Amazon Stores’ Foundational AI organization.