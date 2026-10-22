# https://sam.nlr.gov/software-development-kit-sdk.html

# Software Development Kit (SDK) - System Advisor Model

The SAM Simulation Core (SSC) software development kit (SDK) is a collection of developer tools and documentation including the [PySAM](https://sam.nlr.gov/index.php?option=com_content&view=article&id=104&Itemid=399 "Link to PySAM page") Python package for creating renewable energy system models using the SSC library. SAM is a desktop application that provides a user-friendly front end for the SSC library. The SDK allows you to create your own applications using the SSC library.

If you are using the SDK for the first time, please download and read the SSC guide ([PDF 650 KB](https://sam.nlr.gov/images/web_page_files/ssc_guide.pdf "SSC Guide")) to familiarize yourself with the SSC API, SSC simulation modules, and SDKtool.

Because the SSC simulation modules have a large number of inputs and outputs, we recommend generating your first SSC program from the code generator in SAM's user interface as demonstrated in [this video](https://youtu.be/UUHEoWeJ_L8 "Link to YouTube video demonstrating SAM Code Generator") and described below. The code generator creates a complete set of files for a ready-to-run program written in one of the supported languages and platforms listed below.

#### Where are the language wrappers?

The code generator replaces the language wrappers and examples in older versions of the SDK because it can create a complete set of files for a ready-to-run program for any type of renewable energy project SAM can model, and in any language or operating system supported by the SDK. The old examples were for a limited set of SAM's modeling capabilities and were difficult for us to keep up to date for all operating systems, languages, and platforms.

#### PySAM

If you are developing applications in Python, you might want to use [PySAM](https://sam.nlr.gov/index.php?option=com_content&view=article&id=104&Itemid=399 "Link to PySAM page") for your work. PySAM provides a more robust set of functions for interacting with SSC than are provided by Python code created by SAM's code generator described below.

### Documentation

*   The SSC Guide explaining how to use the tools in the SDK ([PDF 650 KB](https://sam.nlr.gov/images/web_page_files/ssc_guide.pdf "SSC Guide")).
*   The LK Guide describing the SDKtool scripting language ([PDF 272 KB](https://sam.nlr.gov/images/web_page_files/lk_guide.pdf "LK Guide"))
*   Use SDKtool or the API functions described in Section 3.4 of the SSC Guide to explore a simulation module's input and output variables.

### The SSC API

The SSC API, or application programming interface, defines the functions you use in your code to interact with the SSC library. The functions are defined in the `sscapi.h` file. When you use SAM's code generator, SAM includes a copy of the SSC API with the files it generates.

If you generate code in a language other than C, SAM includes a wrapper written in the language that translates the C functions into that language.

### The SSC library

The SSC library is a compiled dynamic library that comes with SAM that you can access from your programs using the SSC API. You can use the SDKtool or the function described in Section 5 of the SDK Guide to determine the version number of the SSC library you are using.

When you create a program using SAM's code generator, it makes a copy of the SSC library to include in the set of files it generates. You can also find the SSC library in the following default locations for each operating system in case you need to find the file yourself:

*   Windows: `c:/SAM/2026.7.3/x64/ssc.dll`
*   macOS: `/Applications/SAM_2026.7.3/ssc.dylib` (See [this forum post](https://sam.nlr.gov/forum/forum-sdk/3271-sdktool-in-sam-2020-11-29-mac-distribution-will-not-start.html "SAM forum post on SDKtool for macOS") for details)
*   Linux: `/home/[username]/SAM/2026.7.3/ssc.so`

### SDKtool

SDKtool is an application that comes with SAM that you can use to explore SSC simulation modules and to write test programs in the LK scripting language. See Chapter 6 of the SSC Guide ([PDF 650 KB](https://sam.nlr.gov/images/web_page_files/ssc_guide.pdf "SSC Guide")) for a description of SDKtool with examples.

The SDKtool is a stand-alone application in your SAM installation folder. You can run it directly from that folder, or move it to a different folder and run it from there.

*   Windows: `c:/SAM/2026.7.3/x64/sdktool.exe`
*   macOS: `/Applications/SAM_2026.7.3/SDKtool` (Use the Finder to open the app.)
*   Linux: `/home/[username]/SAM/2026.7.3/linux_64/SDKtool`

### The SAM Code Generator

![SAM Code Generator](https://sam.nlr.gov/images/web_page_files/code-generator.png)

SAM's code generator generates ready-to-run programs in the languages and platforms listed below from the inputs in a SAM case. Use the code generator to start your programming project to ensure that you use the correct set of simulation modules and set values for all of the inputs they require for your modeling scenario. You can then modify the code to customize the scenario.

*   JSON for inputs
*   PySAM JSON
*   LK for SDKtool
*   C
*   MATLAB
*   Java
*   C#
*   VBA

If you need an SSC interface for the Julia programming language, you can see how we built one for NLR's REopt model in the 'get\_production\_factor()' function in "src/core/production\_factor.jl": [https://github.com/natlabrockies/REopt.jl/blob/e0917a05b304a05deeb1d6ba5b60ccffda698806/src/core/production\_factor.jl#L129](https://github.com/natlabrockies/REopt.jl/blob/e0917a05b304a05deeb1d6ba5b60ccffda698806/src/core/production_factor.jl#L129).

We have removed support for Android and iOS from SAM's code generator, but you may be able to build your own libraries to integrate SAM with applications for those platforms using the following instructions:

*   [Android Studio](https://sam.nlr.gov/11/115 "Link to instructions for SDK for Android Studio")
*   [XCode Swift for iOS](https://sam.nlr.gov/11/116 "Link to instructions for SDK for iOS with XCode and Swift")

### Getting Help

If you have questions or comments about the SDK, please let us know by posting a comment on the [SDK support forum](https://sam.nlr.gov/forum/forum-sdk.html "SDK Support Forum").

## Release Notes

The notes below describe changes to SAM, the SSC, or documentation that are specifically relevant to the SDK.

*   For descriptions of changes to performance or financial models, see the [SAM release notes](https://natlabrockies.github.io/SAM/doc/reference/release_notes.html "SAM Release Notes").
*   For PySAM, see the [PySAM documentation](https://nlr-pysam.readthedocs.io/en/main/versions.html "Link to PySAM documentation").

The list below is for older releases with changes that may not be documented in the current SAM, SSC, or PySAM release notes.

**December 2021**

*   Remove out-of-date Android and iOS from SAM's code generator. (See note above under "The SAM Code Generator.")

**November 11, 2018**

*   Remove language wrappers from SDK package to encourage use of SAM's code generator. This should help resolve version compatibility issues, and help users choose the correct set of simulation modules and variables.
*   Updates to simulation modules as documented in release notes for SAM 2018.11.11.

**June 30, 2015**

*   New PHP 5.4 extension module source code and example PVWatts website HTML code.
*   Updated examples and instructions.

**January 30, 2015**

*   Updated examples and instructions, including LK script and .c files.

**November 24, 2014**

We've updated the examples since the original release on November 24, 2014. The examples should now work with the new simulation modules (as of December 3, 2014).

*   Updates to simulation modules as documented in release notes for SAM 2014.11.24.
*   LK script updates.

**February 5, 2014 (No version number changes)**

*   Resolved SDKtool Windows library depedency issues.

**January 31, 2014 (No version number changes)**

*   Added the msvcp120.dll and msvcr120.dll files required to run SDKtool on Windows 8.1.

**January 21, 2014: SDK 2014-1-21, SSC 36**

*   This is a major update that adds preliminary versions of the concentrating solar power (CSP) modules to the SDK.
*   Revise SSC Guide.

**September 20, 2013: SDK 2013-9-20, SSC 33**

*   Update sample scripts and wrappers to work with SSC 33.

**May 3, 2013: Update to First Release**

*   Added three new modules: CSV weather file reader and converter, plane-of-array calibration, utility rate 2 for new OpenEI utility rate database version 2
*   Updates to support Linux CentOS6.3 and OS X 10.8.
*   Update MATLAB, Java, Python, and LK script examples.
*   Improved the MATLAB wrapper with new classes, SSC package, and a MATLAB GUIDE example.
*   Improved the Python wrapper with new classes, and several examples including flat plate PV with residential and commercial markets.
*   Fixed various issues with the MATLAB and Java wrappers. They have been tested in Windows 32-bit and 64-bit, OS X 10.8, and CentOS 6.3.
*   Updated all wrapper examples to include flat plate PV with residential and commercial markets. They have been tested in Windows 32-bit and 64-bit, OS X 10.8, and CentOS 6.3.

**February 8, 2013: First Release**

*   The first version of the SDK was called Version 0.9.
