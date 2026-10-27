How to customize electricity usage – OpenSolar

 [![OpenSolar Help Center home page](/hc/theming_assets/01M0ZRG0PAHF8XKE2GGHBT6PZZ)](https://support.opensolar.com/hc/en-us "Home")Help Center

English (United States) [Deutsch](https://support.opensolar.com/hc/change_language/de?return_to=%2Fhc%2Fde%2Farticles%2F13183763473295-Anpassung-des-Stromverbrauchs)[Español](https://support.opensolar.com/hc/change_language/es?return_to=%2Fhc%2Fes%2Farticles%2F13183763473295-C%25C3%25B3mo-personalizar-el-consumo-de-electricidad)[Français](https://support.opensolar.com/hc/change_language/fr?return_to=%2Fhc%2Ffr%2Farticles%2F13183763473295-Comment-personnaliser-l-utilisation-de-l-%25C3%25A9lectricit%25C3%25A9)[Italiano](https://support.opensolar.com/hc/change_language/it?return_to=%2Fhc%2Fit%2Farticles%2F13183763473295-Come-personalizzare-il-consumo-di-energia-elettrica)[Nederlands](https://support.opensolar.com/hc/change_language/nl?return_to=%2Fhc%2Fnl%2Farticles%2F13183763473295-Hoe-elektriciteitsverbruik-aan-passen)[Polski](https://support.opensolar.com/hc/change_language/pl?return_to=%2Fhc%2Fpl)[Svenska](https://support.opensolar.com/hc/change_language/sv?return_to=%2Fhc%2Fsv)

[Sign in](https://opensolarhelp.zendesk.com/access?locale=en-us&brand_id=360002000592&return_to=https%3A%2F%2Fsupport.opensolar.com%2Fhc%2Fen-us%2Farticles%2F13183763473295-How-to-customize-electricity-usage&locale=en-us "Opens a dialog")

### Articles in this section

*   [How to customize electricity usage](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage)
*   [How to upload interval data](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data)

# How to customize electricity usage

![](https://support.opensolar.com/system/photos/8966678827023/OS_logo.png)

[OpenSolar Support](https://support.opensolar.com/hc/en-us/profiles/903548256586-OpenSolar-Support)

*   May 08, 2026 17:45
*   Updated

[Follow](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage/subscription.html "Opens a sign-in dialog")

## Summary

OpenSolar enables you to tailor your customer’s electricity usage data to ensure highly accurate proposals. You can input electricity usage manually, estimate it, or derive it from bills. Additional settings allow you to shape daily usage profiles, adjust weekend usage scaling, and account for demand and controlled loads. This guide walks you through the full customization process.

## Table of Contents

*   [Selecting Electricity Usage](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#h_01JZK30R4QYK5KEJC8265W8DCT)
*   [Shaping Electricity Usage Profile](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#h_01JZK32FKZ66TAQER6GAPW26YV)
*   [Scaling Weekend vs. Weekday Usage](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#h_01JZK33P9GG48VF0GHYV4359N5)
*   [Setting Demand Using 8760 Values](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#h_01JZK343EMAV7XXMATMRQ90F3B)
*   [Setting Controlled Loads](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#h_01JZK34QCFYHG0PBNHP28TRPRP)
*   [Video walkthrough](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#h_01JZK35F95AJ9XW8RDFH1BAX21)

## Selecting Electricity Usage:

To begin, open your desired project and go to the **Energy** tab. At the top, you’ll find the **Electricity Usage** section.

Use the **Data Source** dropdown to select the most suitable input method based on available information:

![Screenshot 2025-09-17 at 10.44.17 am.png](/hc/article_attachments/13791406552847)

#### Options for Usage Input:

| **Data Source** | **Description** |
| --- | --- |
| **OpenSolar Usage Estimates** | Use if no customer usage/bill data is available. Choose:   <br>\- _Estimate (Low)_   <br>\- _Estimate (Medium)_ _(Default)_   <br>\- _Estimate (High)_ |
| **Enter kWh Usage** | Use if actual usage is known. Options include:   <br>\- _Daily Consumption (Monthly avg)_   <br>\- _Monthly Consumption_   <br>\- _Quarterly Consumption_   <br>\- _Annual Consumption_   <br>\- _Hourly Interval Data_ (15/30/60-min intervals) |
| **Enter Electricity Bill** | If bills are available and a tariff is set:   <br>\- _Annual Bill_   <br>\- _Quarterly Bills_   <br>\- _Monthly Bills_   <br>\- _Bi-monthly Bill_  <br>Usage is interpolated based on the selected tariff. |

_Note: Missing monthly or quarterly data is automatically interpolated by OpenSolar._

## Shaping Electricity Usage Profile:

> _This step is optional unless you're using hourly interval data._

Once usage is entered, expand **Advanced Settings** and toggle **Configure Usage Profile Curves** to define weekday and weekend usage patterns.

*   Choose a usage curve for weekdays and another for weekends.
*   A live graph displays the selected curve shape.
*   If no curve is selected, the system defaults to **Evening Peak**.

![Screenshot 2025-09-17 at 10.42.30 am.png](/hc/article_attachments/13791415318543)

OpenSolar offers a library of common daily energy profile shapes for various user behaviors.

![mceclip1.png](/hc/article_attachments/13183754585871)

## Scaling Weekend vs. Weekday Usage:

You can fine-tune weekend usage relative to weekdays:

*   Example: If weekend usage is 10% higher than weekday, enter `1.1`.
*   For 50% higher usage, enter `1.5`.

This impacts TOU (Time of Use) calculations and solar self-consumption accuracy.

![Screenshot 2025-09-17 at 10.46.17 am.png](/hc/article_attachments/13791406553359)

## Setting Demand Using 8760 Values:

> _Recommended for accurate demand charge calculations._

If demand is not explicitly set, OpenSolar assumes maximum hourly usage equals hourly demand, which is often inaccurate.

To address this:

*   Upload 15, 30, or 60-minute interval data for an entire year (8760 hours).
*   [See detailed instructions for uploading interval data →](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage#)

## Setting Controlled Loads:

If the household has controlled loads (e.g., water heater):

1.  Expand **Advanced Settings**.
2.  Toggle on **Set Controlled Loads**.
3.  Enter daily usage (in kWh) for up to 3 devices under _Controlled Load 1, 2, 3_.

_Default behavior distributes controlled load usage between 12:00 AM – 5:00 AM._

![Screenshot 2025-09-17 at 10.47.45 am.png](/hc/article_attachments/13791406553743)

### Final Step: Save Your Changes:

Make sure to **save** all your changes before exiting the Energy tab to ensure accurate calculations in the proposal.

## Video walkthrough:

### Related articles

*   [How to select the correct electricity utility/tariff](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCA%2BM%2BJD9CzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2FjiZX9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJbL2hjL2VuLXVzL2FydGljbGVzLzEzMTgzNjg2ODM5MzExLUhvdy10by1zZWxlY3QtdGhlLWNvcnJlY3QtZWxlY3RyaWNpdHktdXRpbGl0eS10YXJpZmYGOwhUOglyYW5raQY%3D--4b29c1f724d560df11cfbfe9a9cfbd77fb7879d6)
*   [How to create a tariff in OpenSolar](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2B9vYpqCzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2FjiZX9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJKL2hjL2VuLXVzL2FydGljbGVzLzEyNTUyMjIyMTI5NTUxLUhvdy10by1jcmVhdGUtYS10YXJpZmYtaW4tT3BlblNvbGFyBjsIVDoJcmFua2kH--089f150550eb1c3182a96855d2d92c7fe8d83a26)
*   [🇬🇧 Battery Control Schemes](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI8a7EGXBzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2FjiZX9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSI%2BL2hjL2VuLXVzL2FydGljbGVzLzgzNDYyMjc0NDg0NjMtLUJhdHRlcnktQ29udHJvbC1TY2hlbWVzBjsIVDoJcmFua2kI--c2e22949bd93e120bd5bed55f5f024018ad3f9e1)
*   [🇬🇧 Design](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCA9RG%2FbjBjoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2FjiZX9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSItL2hjL2VuLXVzL2FydGljbGVzLzc1NzYxNTYzMjgyMDctLURlc2lnbgY7CFQ6CXJhbmtpCQ%3D%3D--5c52bb635c44521293ea7d371a984f5b43048bec)
*   [Add custom cost and price Adders per system](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCBn45FoEBDoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2FjiZX9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJRL2hjL2VuLXVzL2FydGljbGVzLzQ0MTY3NTEzMzU0NDktQWRkLWN1c3RvbS1jb3N0LWFuZC1wcmljZS1BZGRlcnMtcGVyLXN5c3RlbQY7CFQ6CXJhbmtpCg%3D%3D--61a3ea11775d74c222c085d164f7917b0ef34256)

### Comments

0 comments

Please [sign in](https://opensolarhelp.zendesk.com/access?locale=en-us&brand_id=360002000592&return_to=https%3A%2F%2Fsupport.opensolar.com%2Fhc%2Fen-us%2Farticles%2F13183763473295-How-to-customize-electricity-usage) to leave a comment.