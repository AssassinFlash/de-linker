How to upload interval data – OpenSolar

 [![OpenSolar Help Center home page](/hc/theming_assets/01M0ZRG0PAHF8XKE2GGHBT6PZZ)](https://support.opensolar.com/hc/en-us "Home")Help Center

English (United States) [Deutsch](https://support.opensolar.com/hc/change_language/de?return_to=%2Fhc%2Fde%2Farticles%2F13183853699215-Hochladen-Intervalldaten)[Español](https://support.opensolar.com/hc/change_language/es?return_to=%2Fhc%2Fes%2Farticles%2F13183853699215-C%25C3%25B3mo-cargar-datos-de-intervalo)[Français](https://support.opensolar.com/hc/change_language/fr?return_to=%2Fhc%2Ffr%2Farticles%2F13183853699215-Comment-ajout%25C3%25A9e-les-donn%25C3%25A9es-d-intervalle)[Italiano](https://support.opensolar.com/hc/change_language/it?return_to=%2Fhc%2Fit%2Farticles%2F13183853699215-Come-caricare-i-dati-degli-intervalli)[Nederlands](https://support.opensolar.com/hc/change_language/nl?return_to=%2Fhc%2Fnl%2Farticles%2F13183853699215-Intervalgegevens-uploaden)[Polski](https://support.opensolar.com/hc/change_language/pl?return_to=%2Fhc%2Fpl)[Svenska](https://support.opensolar.com/hc/change_language/sv?return_to=%2Fhc%2Fsv%2Farticles%2F13183853699215-Hur-man-laddar-upp-intervalldata)

[Sign in](https://opensolarhelp.zendesk.com/access?locale=en-us&brand_id=360002000592&return_to=https%3A%2F%2Fsupport.opensolar.com%2Fhc%2Fen-us%2Farticles%2F13183853699215-How-to-upload-interval-data&locale=en-us "Opens a dialog")

### Articles in this section

*   [How to customize electricity usage](https://support.opensolar.com/hc/en-us/articles/13183763473295-How-to-customize-electricity-usage)
*   [How to upload interval data](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data)

# How to upload interval data

![](https://support.opensolar.com/system/photos/8966678827023/OS_logo.png)

[OpenSolar Support](https://support.opensolar.com/hc/en-us/profiles/903548256586-OpenSolar-Support)

*   May 08, 2026 17:59
*   Updated

[Follow](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data/subscription.html "Opens a sign-in dialog")

## Summary:

Uploading interval data is the most accurate way to model a customer’s energy consumption and calculate potential solar savings. OpenSolar supports 15, 30, and 60-minute interval data in CSV format and accommodates both **vertical** and **horizontal** data structures. This guide walks you through how to upload, configure, and manage interval data within your project.

## Table of contents:

*   [Uploading Interval Data](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data#h_01JZK4Z81DD3E94C7K5EJ4QX3C)
*   [Data Formats](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data#h_01JZK4Z81G41D0458TD96HB0XG)
*   [Preparing the Data Before You Upload](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data#h_01JZK4Z81KMRX05FJYCBXYSMKD)
*   [Video Walkthrough](https://support.opensolar.com/hc/en-us/articles/13183853699215-How-to-upload-interval-data#h_01JZK4Z81PFVWT2ZDEY8RE85BX)

## Uploading Interval Data:

*   Open your desired **Project** in OpenSolar.
*   Navigate to the **Energy** tab.
*   In the **Electricity Usage** section, select **“Interval Data”** from the **Data Source** dropdown.
*   Select the **Upload CSV** button

![](/hc/article_attachments/13183853698831)

## Data Formats:

OpenSolar accepts the following configurations:

*   **Data Structures**: Vertical or Horizontal
*   **Interval Durations**: 15-minute, 30-minute, or 60-minute intervals

The only files that can be added are our templates that can be downloaded from the Upload CSV window:

![](/hc/article_attachments/13183853698959)

## Preparing the Data Before You Upload:

When you download one of our templates, these can not be edited. The file uploaded must have the same headers as when you download it, or the information will be incorrect.

If your usage information starts on 06/12, find the row 06/12 on our template and place the usage information there. 

*   **Partial Datasets Are Accepted**: You do not need a full calendar year (January–December). The system supports data that:
    *   Spans across years (e.g., June 2024 to May 2025)
    *   Covers less than 12 months
*   **Automatic Extrapolation**: Missing data will be intelligently filled by OpenSolar’s algorithm to estimate full-year values.
*   **Flexible Units**: After uploading, you’ll be prompted to confirm or adjust the unit of measurement used in the file.
*   **Processing Time**: Large datasets, especially at 15-minute intervals, may take slightly longer to process—please be patient.

## Video Walkthrough

### Related articles

*   [How to customize electricity usage](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2FjiZX9CzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2Bg6pr9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJJL2hjL2VuLXVzL2FydGljbGVzLzEzMTgzNzYzNDczMjk1LUhvdy10by1jdXN0b21pemUtZWxlY3RyaWNpdHktdXNhZ2UGOwhUOglyYW5raQY%3D--b8b89e1becf71fc8a6bbd8d0f3d36bd5cab4e956)
*   [How to create and apply a battery control scheme](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2FuOhNSCzoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2Bg6pr9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJXL2hjL2VuLXVzL2FydGljbGVzLzEyNDQ3MTM3ODUzMDcxLUhvdy10by1jcmVhdGUtYW5kLWFwcGx5LWEtYmF0dGVyeS1jb250cm9sLXNjaGVtZQY7CFQ6CXJhbmtpBw%3D%3D--df4c9f952c68b2be05d1f55b636d924dc206509f)
*   [How is Output Calculated in OpenSolar?](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCBkeAvQCBDoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2Bg6pr9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJLL2hjL2VuLXVzL2FydGljbGVzLzQ0MTA3MzAyMjUxNzctSG93LWlzLU91dHB1dC1DYWxjdWxhdGVkLWluLU9wZW5Tb2xhcgY7CFQ6CXJhbmtpCA%3D%3D--1ddf5d0e1ed434fd01fb5d9efcdddb3c68070a43)
*   [What is Solar Compensation Mechanism on an Electricity Tariff Rate?](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCI%2FvSaq9BjoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2Bg6pr9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJoL2hjL2VuLXVzL2FydGljbGVzLzc0MTE2NzU1NTc3NzUtV2hhdC1pcy1Tb2xhci1Db21wZW5zYXRpb24tTWVjaGFuaXNtLW9uLWFuLUVsZWN0cmljaXR5LVRhcmlmZi1SYXRlBjsIVDoJcmFua2kJ--baec7c4ab2db07f0c46c14757c7d9960ba8ea3f6)
*   [How to make Changes to a Sold/Accepted System](https://support.opensolar.com/hc/en-us/related/click?data=BAh7CjobZGVzdGluYXRpb25fYXJ0aWNsZV9pZGwrCBk6AOICBDoYcmVmZXJyZXJfYXJ0aWNsZV9pZGwrCI%2Bg6pr9CzoLbG9jYWxlSSIKZW4tdXMGOgZFVDoIdXJsSSJTL2hjL2VuLXVzL2FydGljbGVzLzQ0MTA0MjgxMTEzODUtSG93LXRvLW1ha2UtQ2hhbmdlcy10by1hLVNvbGQtQWNjZXB0ZWQtU3lzdGVtBjsIVDoJcmFua2kK--4ad2e32622853009dc9e6203e32cf9bcfa3e455a)

### Comments

0 comments

Please [sign in](https://opensolarhelp.zendesk.com/access?locale=en-us&brand_id=360002000592&return_to=https%3A%2F%2Fsupport.opensolar.com%2Fhc%2Fen-us%2Farticles%2F13183853699215-How-to-upload-interval-data) to leave a comment.