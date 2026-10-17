<!-- source: https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html
     loadedTime(UTC): 2026-10-17T05:31:53.509Z
     httpStatus: 200
     apifyRun: TrRwuJPIOXuAAY33r (wcc-known-1) -->

# Understanding Success Criterion 3.2.1: On Focus | WAI

## Understanding [SC 3.2.1](https://w3.org/TR/WCAG22#on-focus) On Focus (Level A)

## In Brief

Goal

Content can be navigated more predictably.

What to do

Do not change a user's context when items get focus.

Why it's important

Content that behaves predictably is especially important to people with disabilities.

When any [user interface component](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-user-interface-component) receives focus, it does not initiate a [change of context](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-changes-of-context).

## Intent

The intent of this success criterion is to ensure that functionality is predictable as visitors navigate their way through a document. Any component that is able to trigger an event when it receives focus must not change the context. Examples of changing context when a component receives focus include, but are not limited to:

*   forms submitted automatically when a component receives focus;
*   new windows launched when a component receives focus;
*   focus is changed to another component when that component receives focus;

Focus may be moved to a control either via the keyboard (e.g. tabbing to a control) or the mouse (e.g. clicking on a text field). Moving the mouse over a control does not move the focus unless scripting implements this behavior. Note that for some types of controls, clicking on a control may also activate the control (e.g. button), which may, in turn, initiate a change in context.

Note

What is meant by "component" here is also sometimes called "user interface element" or "user interface component".

## Benefits

*   This success criterion helps people with visual disabilities, cognitive limitations, and motor impairments by reducing the chance that a change of context will occur unexpectedly.

## Examples

Example 1: A dropdown menu

A dropdown menu on a page allows users to choose between jump destinations. If the person uses the keyboard to move down to a choice and activates it (with a spacebar or enter key) it will jump to a new page. However, if the person moves down to a choice and either hits the escape or the tab key to move out of the pulldown menu – it does not jump to a new screen as the focus shifts out of the dropdown menu.

Example of a Failure: A help dialog

When a field receives focus, a help dialog window describing the field and providing options opens. As a keyboard user tabs through the web page, the dialog opens, moving the keyboard focus away from the control every time the user attempts to tab past the field.

## Techniques

Each item in this section represents a technique or combination of techniques that the Accessibility Guidelines Working Group deems sufficient for meeting this success criterion. A technique may go beyond the minimum requirement of the criterion. There may be other ways of meeting the criterion not covered by these techniques. For information on using other techniques, see [Understanding Techniques for WCAG Success Criteria](https://www.w3.org/WAI/WCAG22/Understanding/understanding-techniques), particularly the "Other Techniques" section.

### Sufficient Techniques

*   [G107: Using "activate" rather than "focus" as a trigger for changes of context](https://www.w3.org/WAI/WCAG22/Techniques/general/G107)

Note

A change of content is not always a [change of context](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-changes-of-context). This success criterion is automatically met if changes in content are not also changes of context.

### Failures

The following are common mistakes that are considered failures of this success criterion by the Accessibility Guidelines Working Group.

*   [F55: Failure of Success Criteria 2.1.1, 2.4.7, 2.4.13, and 3.2.1 due to using script to remove focus when focus is received](https://www.w3.org/WAI/WCAG22/Techniques/failures/F55)

## Key Terms

assistive technology

hardware and/or software that acts as a [user agent](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-user-agent), or along with a mainstream user agent, to provide functionality to meet the requirements of users with disabilities that go beyond those offered by mainstream user agents

Note 1

Functionality provided by assistive technology includes alternative presentations (e.g., as synthesized speech or magnified content), alternative input methods (e.g., voice), additional navigation or orientation mechanisms, and content transformations (e.g., to make tables more accessible).

Note 2

Assistive technologies often communicate data and messages with mainstream user agents by using and monitoring APIs.

Note 3

The distinction between mainstream user agents and assistive technologies is not absolute. Many mainstream user agents provide some features to assist individuals with disabilities. The basic difference is that mainstream user agents target broad and diverse audiences that usually include people with and without disabilities. Assistive technologies target narrowly defined populations of users with specific disabilities. The assistance provided by an assistive technology is more specific and appropriate to the needs of its target users. The mainstream user agent may provide important functionality to assistive technologies like retrieving web content from program objects or parsing markup into identifiable bundles.

changes of context

major changes that, if made without user awareness, can disorient users who are not able to view the entire page simultaneously

Changes in context include changes of:

*   [user agent](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-user-agent);
*   [viewport](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-viewport);
*   focus;
*   [content](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-content) that changes the meaning of the [web page](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-web-page)

Note

A change of content is not always a change of context. Changes in content, such as an expanding outline, dynamic menu, or a tab control do not necessarily change the context, unless they also change one of the above (e.g., focus).

content

information and sensory experience to be communicated to the user by means of a [user agent](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-user-agent), including code or markup that defines the content's [structure](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-structure), [presentation](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-presentation), and interactions

presentation

rendering of the [content](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-content) in a form to be perceived by users

structure

*   The way the parts of a [web page](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-web-page) are organized in relation to each other; and
*   The way a collection of [web pages](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-web-page) is organized

user agent

any software that retrieves and presents web content for users

user interface component

a part of the content that is perceived by users as a single control for a distinct function

Note 1

Multiple user interface components may be implemented as a single programmatic element. "Components" here is not tied to programming techniques, but rather to what the user perceives as separate controls.

Note 2

User interface components include form elements and links as well as components generated by scripts.

Note 3

What is meant by "component" or "user interface component" here is also sometimes called "user interface element".

viewport

object in which the [user agent](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-user-agent) presents content

Note 1

The user agent presents content through one or more viewports. Viewports include windows, frames, loudspeakers, and virtual magnifying glasses. A viewport may contain another viewport (e.g., nested frames). Interface components created by the user agent such as prompts, menus, and alerts are not viewports.

web page

a non-embedded resource obtained from a single URI using HTTP plus any other resources that are used in the rendering or intended to be rendered together with it by a [user agent](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#dfn-user-agent)

Note 1

Although any "other resources" would be rendered together with the primary resource, they would not necessarily be rendered simultaneously with each other.

Note 2

For the purposes of conformance with these guidelines, a resource must be "non-embedded" within the scope of conformance to be considered a web page.

[Back to Top](https://www.w3.org/WAI/WCAG22/Understanding/on-focus.html#top)