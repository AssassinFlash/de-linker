<!-- source: https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows
     loadedTime(UTC): 2026-10-17T05:43:37.099Z
     httpStatus: 200
     apifyRun: 441FEIMGdGRPUOGLw (wcc-b4-lists) -->

Use Fin AI Agent in Workflows | Intercom Help

[Skip to main content](https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows#docs-main)

*   [Overview](https://www.intercom.com/help/en/collections/382-overview "Overview")
    
*   [Getting Started](https://www.intercom.com/help/en/collections/1865264-getting-started "Getting Started")
    
*   [Fin AI Agent](https://www.intercom.com/help/en/collections/6485365-fin-ai-agent "Fin AI Agent")
    
    *   [Fin AI Agent explained](https://www.intercom.com/help/en/articles/7120684-fin-ai-agent-explained "Fin AI Agent explained")
    *   [Fin for platforms explained](https://www.intercom.com/help/en/articles/10118495-fin-for-platforms-explained "Fin for platforms explained")
    *   [Fin memory](https://www.intercom.com/help/en/articles/16001516-fin-memory "Fin memory")
    *   [Roles](https://www.intercom.com/help/en/collections/15902891-roles "Roles")
        
    *   [Fin Operator](https://www.intercom.com/help/en/collections/19634087-fin-operator "Fin Operator")
        
    *   [Train](https://www.intercom.com/help/en/collections/3990230-train "Train")
        
    *   [Test](https://www.intercom.com/help/en/collections/4009151-test "Test")
        
    *   [Deploy](https://www.intercom.com/help/en/collections/6486559-deploy "Deploy")
        
        *   [Introduction to Deploy](https://www.intercom.com/help/en/articles/11769044-introduction-to-deploy "Introduction to Deploy")
        *   [Choose channels to deploy Fin AI Agent](https://www.intercom.com/help/en/articles/13377077-choose-channels-to-deploy-fin-ai-agent "Choose channels to deploy Fin AI Agent")
        *   [Deploy Fin AI Agent over chat](https://www.intercom.com/help/en/articles/8286630-deploy-fin-ai-agent-over-chat "Deploy Fin AI Agent over chat")
        *   [Deploy Fin AI Agent over email](https://www.intercom.com/help/en/articles/9356221-deploy-fin-ai-agent-over-email "Deploy Fin AI Agent over email")
        *   [Customize Fin AI Agent in the Messenger](https://www.intercom.com/help/en/articles/7837525-customize-fin-ai-agent-in-the-messenger "Customize Fin AI Agent in the Messenger")
        *   [Use Fin AI Agent in Workflows](https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows "Use Fin AI Agent in Workflows")
        *   [Let Fin AI Agent follow up after Outbound messages or Workflows](https://www.intercom.com/help/en/articles/8194403-let-fin-ai-agent-follow-up-after-outbound-messages-or-workflows "Let Fin AI Agent follow up after Outbound messages or Workflows")
        *   [Hand over Fin AI Agent conversations to another support tool](https://www.intercom.com/help/en/articles/7995955-hand-over-fin-ai-agent-conversations-to-another-support-tool "Hand over Fin AI Agent conversations to another support tool")
        *   [Deploy Fin AI Agent fast with Workflows templates](https://www.intercom.com/help/en/articles/13514464-deploy-fin-ai-agent-fast-with-workflows-templates "Deploy Fin AI Agent fast with Workflows templates")
        *   [Deploy Fin AI Agent over Discord](https://www.intercom.com/help/en/articles/11868746-deploy-fin-ai-agent-over-discord "Deploy Fin AI Agent over Discord")
        *   [Deploy Fin Voice](https://www.intercom.com/help/en/collections/18533316-deploy-fin-voice "Deploy Fin Voice")
            
        
    *   [Analyze](https://www.intercom.com/help/en/collections/3990231-analyze "Analyze")
        
    *   [Fin settings](https://www.intercom.com/help/en/collections/15897976-fin-settings "Fin settings")
        
    *   [FAQs](https://www.intercom.com/help/en/collections/3990234-faqs "FAQs")
        
    
*   [Channels](https://www.intercom.com/help/en/collections/10723236-channels "Channels")
    
*   [Inbox](https://www.intercom.com/help/en/collections/3497068-inbox "Inbox")
    
*   [Workflows](https://www.intercom.com/help/en/collections/2094721-workflows "Workflows")
    
*   [Knowledge](https://www.intercom.com/help/en/collections/9615439-knowledge "Knowledge")
    
*   [Reports](https://www.intercom.com/help/en/collections/2094752-reports "Reports")
    
*   [Outbound](https://www.intercom.com/help/en/collections/2091449-outbound "Outbound")
    
*   [Contacts](https://www.intercom.com/help/en/collections/2094808-contacts "Contacts")
    
*   [Workforce Management](https://www.intercom.com/help/en/collections/19649382-workforce-management "Workforce Management ")
    
*   [Apps & Integrations](https://www.intercom.com/help/en/collections/2094744-apps-integrations "Apps & Integrations")
    
*   [Mobile SDKs](https://www.intercom.com/help/en/collections/2094798-mobile-sdks "Mobile SDKs")
    
*   [Community](https://www.intercom.com/help/en/collections/2847869-community "Community")
    
*   [Academy](https://www.intercom.com/help/en/collections/2493871-academy "Academy")
    
*   [Security & Privacy](https://www.intercom.com/help/en/collections/384-security-privacy "Security & Privacy")
    

Use this article to add Fin AI Agent to your [Workflows](https://www.intercom.com/help/en/articles/7836459-workflows-explained), customize its handover behavior, configure channel-specific settings, troubleshoot conflicts with existing workflows, and preview Fin before going live. You can set up Fin to respond within a workflow, or configure workflows to pass conversations to Fin. Fin AI Agent is available on paid plans. You'll need admin permissions to create or edit Workflows.

* * *

# Add Fin to a Workflow

Go to [Fin AI Agent > Workflows](https://app.intercom.com/a/apps/_/automation/workflows-overview) to get started. You can add Fin to an existing workflow, or create a new one. The best workflow triggers to use with Fin are:

*   **When customer opens a new conversation in the Messenger** \- use this if you want Fin to immediately introduce itself in the Messenger and respond to customers' questions.
    
*   **When customer sends their first message** - use this if you want Fin to respond to customers' questions across alternative channels (WhatsApp, Instagram, SMS, etc.)
    

<signed-url-removed>

## Choose which workflow channels Fin is enabled on

To enable Fin on particular channels or for a specific audience, click on the workflow trigger settings (trigger block in the Workflows builder).

<signed-url-removed>

If you're creating a workflow for email, you can add audience rules [using email predicates](https://www.intercom.com/help/en/articles/6884847-omnichannel-support-for-workflows#h_5b2cc50914).

**Note:**

*   Channel selection is only available when using triggers such as "When customer sends their first message" or "When customer sends any message".
    
*   When adding Fin to email workflows, you must use the "When customer sends their first message" trigger or choose the "Use Fin AI Agent over Email" template if you're building a new workflow.
    
*   Not all Workflow steps are available over email. Check [what actions are compatible with this channel](https://www.intercom.com/help/en/articles/6884847-omnichannel-support-for-workflows#:~:text=not%20run%20again.-,Channel%20compatibility,-The%20table%20below). For this reason, we recommend creating a separate workflow solely for using Fin over email.
    

## Add Let Fin answer step

Then add Fin to your workflow by creating a path and selecting **Let Fin answer**. This inserts a **Let Fin handle** step which can then be configured to control the behavior and handover. Once inserted, click the **Let Fin handle** step to open its settings panel and configure behavior, handover, and auto-close options.

<signed-url-removed>

The **Let Fin handle** step triggers a response _after_ a customer sends a message — Fin does not automatically respond to quick-reply button selections. To address this, add a message action after the button prompting the customer to type their question, or use canned replies on specific buttons to provide an immediate answer.

Human in the Loop only works in conversations that reach a **Let Fin handle** step. You can also set up Human in the Loop in the Fin step. [Learn more](https://www.intercom.com/help/en/articles/16198358-ask-a-teammate-for-help-with-fin-s-replies-human-in-the-loop).

Your workspace [office hours](https://www.intercom.com/help/en/articles/732390-set-your-default-office-hours) will always be respected when Fin does a handover from a workflow.

## Create different experiences for different audiences

By using [branching](https://www.intercom.com/help/en/articles/7846212-using-branches-in-workflows), you can create different Fin AI Agent experiences for different audiences.

For example, for paying customers, you might want to hand over to a teammate when Fin can't answer but for non-paying customers, you might want to direct them to your Help Center.

<signed-url-removed>

For greater flexibility with email workflows, use the [“Email to", "Email cc", and "Email Bcc" predicates](https://www.intercom.com/help/en/articles/6884847-omnichannel-support-for-workflows#h_5b2cc50914) if you would like to create different auto-reply messages (and other steps and actions) depending on the email address a customer sends their message to.

# Customize Fin's behavior in a Workflow

To customize Fin's behavior in a workflow, click on the **Let Fin handle** step in the workflow path.

<signed-url-removed>

**Note:** The settings below — including CSAT, follow-up, and auto-close — are only interactive when the workflow is in **Edit** mode. If you open a Fin workflow without clicking **Edit** first, none of these toggles can be turned on or off.

## Settings for chat channels

### Set expectation for human support

For chat conversations, if you don't want Fin to hand over to a teammate, you can configure the step to not set any expectations for human support.

**Notes**:

*   Any messages you add to a workflow with Fin over email will be sent as one email. This also applies to any messages you've configured to be sent as follow-up messages when a customer goes inactive in a Fin conversation.
    
*   When turning off the "Set expectation for human support" option, the Auto-close pending Fin conversations checkboxes in the same settings panel will be disabled, as this option was built for situations where the user is escalated to a human.
    

### Ask for more information before handover

For chat conversations, you can ask Fin to gather more information from a customer before passing to your team:

1.  Click on the **Let Fin handle** step in your workflow.
    
2.  Select **Ask for more information before handover**.
    
3.  Enable "Collect more information when a customer asks to speak to the team".
    

<signed-url-removed>

Fin will encourage the user to share more information. The exact message it sends will be similar to "_Sure! While I connect you, could you provide us with more details about your issue to help us find an answer faster?_" This will be adapted to the context of the conversation and your workspace’s Fin personality settings.

By prompting the customer for more context before Fin hands over to a teammate, there is another opportunity to get more and/or better information than presented the first time around. The benefit to this is two-fold:

1.  Gives Fin another chance to answer: often customers don’t give the AI Agent a chance, asking to speak to a human before asking Fin a question.
    
2.  If context is provided, even if Fin can’t provide an answer, the teammate will spend less time gathering context and will be able to troubleshoot faster.
    

We've tested this feature extensively at Intercom and observed an increase in answer rate, confirmed resolutions, and CSAT.

**Note:**

*   If the customer doesn't reply to Fin's prompt for more information, or if Fin is unable to find an answer to a new query, the conversation will be automatically escalated to the team (this will not count as a resolution).
    
*   If Fin does find an answer to a new query, then it will only escalate them to the team if the customer's reply indicates they still need help. If the customer replies they got the help they needed, the conversation will be regarded as a confirmed resolution, and if they abandon the conversation, it will be regarded as an assumed resolution.
    

### Follow-up with inactive customers

At the end of the conversation, you can decide what happens if the customer hasn't responded after Fin answers:

*   **Fin will confirm whether the user still needs assistance:** Select this if you'd like Fin to handle as much as possible.
    
*   **Fin will offer escalation:** Select this if you'd like to involve human support more often.
    
*   **No follow up:** Fin doesn't send any additional messages after responding.
    

<signed-url-removed>

**Note:** The inactivity timer is set to 4 minutes over chat channels and isn't configurable.

**Note: Fin for Sales — follow-up and auto-close differences**

If you're using Fin for Sales steps in your workflow, there are two important differences from standard Fin behavior:

*   The follow-up timer only starts after Fin sends its own first reply. If the lead goes silent before Fin has responded — for example, if Fin didn't send a message before the customer became inactive — the timer never begins and no follow-up is triggered.
    
*   The "Auto-close abandoned conversations" setting is not available on Fin for Sales steps. This option only applies to standard Let Fin handle steps. If you need to close abandoned conversations in a Fin for Sales workflow, use a separate inactivity workflow with the "Customer has been unresponsive" trigger.
    

## Settings for email channel

### Follow-up with inactive customers

If using Fin over email, you can configure what happens if the customer doesn't respond after Fin's email:

*   **No follow up:** Fin doesn't send any additional emails after responding.
    
*   **Fin will confirm whether the user still needs assistance:** Select this if you'd like Fin to handle as much as possible.
    

If you'd like Fin to follow-up, you can also specify the duration to wait before checking if the customer still needs help (from 1 hour up to 30 days; defaults to 24 hours) and customize the follow-up message.

<signed-url-removed>

### CC behavior and reply scope

When using Fin over email in a workflow, you can also configure how Fin handles multi-participant threads directly within the **Let Fin answer** settings panel. These settings operate independently from the deployment-level settings in [Fin AI Agent > Deploy > Email](https://app.intercom.com/a/apps/_/automation/fin-ai-agent/deploy/email).

*   CC behavior — choose whether Fin responds when it's only addressed in CC (not a direct recipient). Default: reply to all emails.
    
*   Reply scope — choose whether Fin replies to all participants or only to the original sender. Default: reply all.
    

**Note:** If you configure these settings at the workflow step level, they apply to that workflow only. Configuring them in the **Simple deploy** settings applies them as the default for all email conversations Fin handles outside of workflows. Both sets of settings default to existing behavior — no change occurs until you explicitly opt in.

## Settings for all channels

### Ask for conversation rating (CSAT)

At the end of a customer's interaction with Fin, you can ask them to give a conversation rating (CSAT — Customer Satisfaction score) by toggling these settings on:

*   Send CSAT if customer gives positive feedback
    
*   Send CSAT if the customer becomes inactive after Fin showed an answer
    
*   Prevent customers from changing their initial rating after a period of time
    

<signed-url-removed>

[Learn more about Fin AI Agent CSAT](https://www.intercom.com/help/en/articles/8368157-fin-csat).

### Auto-close abandoned Fin conversations

Choose when to auto-close conversations by specifying a length of time Fin should wait before a customer is considered inactive. If you've enabled a [follow-up](https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows#h_89cddf25d7), it will be sent 4 minutes after the last customer message. Once the follow-up is sent, the auto-close timer configured in the settings beneath will begin.

Then select if you want Fin to automatically **close the conversation after customer becomes inactive**:

*   If Fin has answered the question, and/or
    
*   If Fin was not able to answer the question, and/or
    
*   If the customer left before asking any questions.
    

You can also **Customize what Fin says when closing the conversation** to make sure the customer got what they needed and remind them they can still speak to your support team, even if the conversation is being closed.

<signed-url-removed>

* * *

# When Fin closes a conversation

Use the **When Fin closes a conversation** trigger to automatically run a workflow whenever Fin closes a conversation. Unlike the **Teammate changes the state of a conversation** trigger, this fires on Fin-initiated closures only — giving you precise control over post-resolution automation.

1.  Go to [Fin AI Agent > Workflows](https://app.intercom.com/a/apps/_/automation/workflows-overview) and create a new workflow.
    
2.  Select **When Fin closes a conversation** as the trigger.
    
    <signed-url-removed>
    
3.  Select one or more close reasons to control when the workflow fires:
    
    *   **Confirmed resolution** — the customer confirmed Fin answered their question
        
    *   **Inactivity** — the customer stopped responding and the conversation timed out
        
    *   **Other** — any other close reason
        
    
    <signed-url-removed>
    
4.  Add your workflow actions, such as sending a CSAT survey, adding a tag, or assigning the conversation to a team.
    

**Tip**: Use the confirmed resolution filter to send CSAT surveys only to customers Fin successfully helped, and the inactivity filter to tag or route conversations where the customer went quiet without a clear resolution.

**Note**: This trigger only fires when Fin closes a conversation. For closures initiated by a teammate, use the **Teammate changes the state of a conversation** trigger.

* * *

# Configure Fin's handover

Fin escalates conversations based on natural language cues — such as a direct request for human support, negative feedback, or repeated replies without resolution. If the customer gives positive feedback, Fin closes the conversation and marks it as resolved. Ensure assignment settings are configured to automatically assign escalated conversations to the appropriate team or individual.

This doesn't prevent the customer asking follow up questions.

If the customer gives negative feedback (e.g. _"No that didn't help"_), they will follow a handover path that you will need to configure in the workflow.

<signed-url-removed>

For example, you could set expectations for when your team will reply or collect additional information that will help route the conversation to the right team. This helps make the transition as smooth as possible and can save teammates' time and effort when picking up the conversation.

**Note:**

*   If a customer sends a message similar to "talk to a person" as their first message when Fin is triggered, Fin will follow the handover path without trying to generate a response.
    
*   Fin continues to respond in a conversation until one of the following happens: a teammate sends a customer-facing reply, or Fin ends the session itself via escalation or handover. Reassigning the conversation to a teammate, changing the ticket state, or leaving an internal note does not stop Fin — only a reply visible to the customer ends Fin's session.
    

## Pass to a reusable workflow

You can also [pass to a reusable workflow](https://www.intercom.com/help/en/articles/6398853-reusable-workflows) if you have a common triage or data collection process that you want it to follow. Use the **Pass to a reusable workflow** step to hand Fin over to another workflow.

<signed-url-removed>

**Note:** The [reusable Workflow](https://www.intercom.com/help/en/articles/6398853-link-bots-with-reusable-workflows) must be created before you can set this up.

* * *

# Trigger a Fin reusable workflow from the inbox

You can add a **Let Fin handle** step to a [reusable workflow](https://www.intercom.com/help/en/articles/6398853-reusable-workflows) and trigger Fin directly from the Inbox. Fin requires a message from a customer after the workflow is triggered before it will generate a response.

Fin requires a message from the customer before it generates a response. To handle this, add a message action before the **Let Fin handle** step asking the customer to type or clarify their question, as shown below:

<signed-url-removed>

* * *

# Preview a Fin workflow

When you add Fin to a workflow, you'll be able to experience a conversation with Fin using your workflow.

First **Save** your new workflow, then click the **Preview** button at the top of the Workflows builder.

<signed-url-removed>

This will give you an interactive preview of the experience when talking to Fin. Simply start asking questions you would expect to find answers to in the support content you added.

<signed-url-removed>

If you want to test a Fin workflow over email, send an email to your support email address configured to receive email in Intercom or to the email address in [Settings > Email > Email forwarding](https://app.intercom.com/a/apps/_/settings/email-forwarding).

You can also preview Fin from any website where you have the Messenger installed. Click **Preview from a website** and enter the address, then click **Open website** to load the Messenger with Fin on that website.

<signed-url-removed>

**Note:** To preview Fin from a website, it'll need to be set live and you must have the [Messenger installed](https://www.intercom.com/help/en/articles/168-install-intercom-in-your-product-for-logged-in-users).

* * *

# Conflicts with existing Workflows

If you are using other Workflows alongside Fin AI Agent, there are 2 triggers where they could conflict with each other.

### 1\. Customer sends their first message

When both Fin's Simple deployment and workflows are enabled for the same audience, Simple deployment takes priority and only Fin will respond. To allow workflows to trigger, adjust audience targeting so they do not overlap, or disable Simple deployment. In certain scenarios, Fin may continue to respond even after a human agent takes over because of overlapping triggers like "Customer sends any message". To prevent this, adjust workflow configurations to ensure Fin does not re-engage when a teammate is active, and review triggers for unintended overlaps.

**Important:** Do not use the **Customer sends any message** trigger in a workflow that contains a Fin step. Because this trigger fires on every customer message, Fin will keep replying indefinitely — including after a human agent has taken over the conversation. This causes Fin to interject in live human-to-customer exchanges. Use **Customer sends their first message** or **Customer opens a new conversation in the Messenger** instead.

### 2\. Customer opens a new conversation in the Messenger

Workflow will be shown with reply buttons. Clicking on a reply button means entering the Workflow and Fin AI Agent will not fire.

If you leave the composer open (**Let customer type**), customers can still type in their question and Fin AI Agent will take over (Workflow will be skipped).

<signed-url-removed>

However, if you disable the text composer in the first step of the Workflow, Fin will be blocked.

<signed-url-removed>

If Fin is being blocked because the composer is disabled at the start of the workflow, here are some troubleshooting tips:

*   Enable **Let customer type** option at the start of the Workflow, to ensure customers have the option of typing a message (and Fin will respond).
    
*   Use the [Let Fin handle](https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows#h_75ef82b882) step later in the Workflow, preferably after a button says ‘Ask a question’.
    
*   Ensure the audience targeting for workflows with Fin don't overlap with other workflows.
    
*   To verify Fin is correctly set up, confirm that Fin is enabled for the Messenger and deployed via Simple deployment or Advanced Workflows. Fin only participates in new conversations where it is explicitly enabled.
    

* * *

💡**Tip**

**Need more help?** Get support from our [Community Forum](https://community.intercom.com/?utm_source=ii-help-center&utm_medium=internal)  
Find answers and get help from Intercom Support and Community Experts

* * *

Did this answer your question?

Disappointed ReactionNeutral ReactionSmiley Reaction

## Related Articles

*   [Deploy Fin AI Agent over chat](https://www.intercom.com/help/en/articles/8286630-deploy-fin-ai-agent-over-chat)
*   [Analyze and report on Fin AI Agent CSAT](https://www.intercom.com/help/en/articles/8368157-analyze-and-report-on-fin-ai-agent-csat)
*   [Deploy Fin AI Agent over email](https://www.intercom.com/help/en/articles/9356221-deploy-fin-ai-agent-over-email)
*   [Use Fin Voice in phone Workflows](https://www.intercom.com/help/en/articles/12918513-use-fin-voice-in-phone-workflows)
*   [Deploy Fin AI Agent fast with Workflows templates](https://www.intercom.com/help/en/articles/13514464-deploy-fin-ai-agent-fast-with-workflows-templates)