# https://github.com/NatLabRockies/SAM/wiki/Mac-Build-Instructions

# Mac Build Instructions · NatLabRockies/SAM Wiki · GitHub

These instructions were last tested in October 2024 on macOS 15.1 Sequoia using the following:

*   Xcode 16.1
*   CMake 3.30.5 (minimum CMake 3.24)
*   wxWidgets 3.2.8.1
*   GoogleTest 1.14.0
*   OR-Tools v9.14
*   Git 2.39.2
*   GNU Make 3.81

Builds should work on computers running macOS 12 or later with either Apple Silicon or Intel processors.

Before building SAM, you must build GoogleTest and wxWidgets from source.

> **Note** These instructions place code repositories in your mac's Home directory using the `$HOME` environment variable. This makes it possible for you to copy and paste commands from the instructions to your Terminal. If you want to use different directories for your installation, replace "$HOME" in the instructions with a different directory path.

To [install Command Line Tools](https://mac.install.guide/commandlinetools/4.html), open a terminal window, and type the following command:

```
xcode-select --install
```

If Command Line Developer tools is not installed, you should see a message asking if you want to install them. Click **Install**.

The SAM build uses [CMAKE](https://cmake.org/install/) to generate makefiles.

1.  Download the appropriate pre-compiled binary distribution appropriate for your Mac and copy `CMake.app` to the Applications directory.
    
2.  Add a symbolic link to `/usr/local/bin` (assuming you copied CMake to your Applications directory) to make CMake available for the command line.
    
    ```
    /Applications/CMake.app/Contents/bin/cmake-gui --install
    ```
    

To see other ways to enable CMake for the command line, in the CMake application, go to **Tools, How to Install for Command Line Use**.

SAM builds require at least the version of wxWidgets shown above, it may work with more recent versions.

1.  Download source code for macOS from [https://www.wxwidgets.org/downloads/](https://www.wxwidgets.org/downloads/).
    
    If the latest version available for download is newer than the one SAM requires, follow the link under "Other Downloads" at the bottom of the page to find the source code for the older version.
    
2.  [Extract](https://www.thegeekstuff.com/2010/04/unix-tar-command-examples/) the downloaded archive with Finder or the following command:
    
    ```
    tar xvfj $HOME/Downloads/wxWidgets-3.2.8.1.tar.bz2 $HOME/
    ```
    
    This example extracts the source code to a `wxWidgets-3.2.8.1` directory in your Home directory, but you can put it in a directory other than your Home directory.
    
    The `$HOME/wxWidgets-3.2.8.1` directory should contain several files and folders including `CMakeLists.txt`, `README.md`, and a `build` directory.
    
3.  Go to the `build` directory.
    
    ```
    cd $HOME/wxWidgets-3.2.8.1/build
    ```
    
4.  Run `configure` to generate makefiles.
    
    ```
    ../configure --prefix=$HOME/local/wx-3.2.8.1/Release --enable-stl=yes --enable-shared=no --disable-debug_flag --with-cocoa --enable-universal_binary=x86_64,arm64 --enable-unicode --enable-webview --disable-mediactrl --with-cxx=11 --with-macosx-version-min=12  --with-libjpeg=builtin --with-libpng=builtin --with-regex=builtin --with-libtiff=builtin --with-zlib=builtin --with-expat=builtin
    ```
    
    If you are having trouble finding the correct MacOSX SDK, which results in C++ stdlib headers such as `<string>` not being found, try specifying the location of the MacOSX SDK that is compatible with MacOSX version 12:
    
    ```
    export SDKPATH=/Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk
    
    ../configure \
      --prefix=$HOME/local/wx-3.2.8.1/Release \
      --enable-stl=yes --enable-shared=no --disable-debug_flag \
      --with-cocoa --enable-universal_binary=x86_64,arm64 \
      --enable-unicode --enable-webview --disable-mediactrl \
      --with-cxx=17 --with-macosx-version-min=12 \
      --with-libjpeg=builtin --with-libpng=builtin --with-regex=builtin \
      --with-libtiff=builtin --with-zlib=builtin --with-expat=builtin \
      CXXFLAGS="-isysroot $SDKPATH -isystem $SDKPATH/usr/include/c++/v1" \
      CFLAGS="-isysroot $SDKPATH" \
      OBJCXXFLAGS="-isysroot $SDKPATH -isystem $SDKPATH/usr/include/c++/v1" \
      LDFLAGS="-isysroot $SDKPATH"
    ```
    
5.  Run `make` to generate non-source files and install wxWidgets.
    
    ```
    $ make clean
    $ make
    $ make install
    ```
    
    This installs wxWidgets in `~/local/wx-3.2.8.1`.
    
    > **Note.** Use `make -j'nproc'` to run jobs in parallel for a faster build. See [this StackExchange discussion for details](https://unix.stackexchange.com/questions/208568/how-to-determine-the-maximum-number-to-pass-to-make-j-option).
    
6.  Create a symbolic link to the wxWidgets installation directory so that the SAM build process can find the files it needs.
    
    ```
    ln -s ~/local/wx-3.2.8.1/Release/bin/wx-config /usr/local/bin/wx-config-3
    ```
    
    Use `-sf` to overwrite an existing symoblic link.
    
7.  Test the installation.
    
    ```
    wx-config-3 --cflags
    ```
    
    If the installation was successful, you should see:
    
    ```
    -I/Users/[user]/local/wx-3.2.8.1/lib/wx/include/osx_cocoa-unicode-static-3.2 -I/Users/[user]/local/wx-3.2.8.1/include/wx-3.2 -D_FILE_OFFSET_BITS=64 -DwxDEBUG_LEVEL=0 -D__WXMAC__ -D__WXOSX__ -D__WXOSX_COCOA__ 
    ```
    

SAM's repositories depend on Google's C++ unit-test framework [Google Test](https://github.com/google/googletest).

1.  Clone the GoogleTest repository into a directory of your choice. This example uses the Home directory, but you can choose a different one.
    
    ```
    cd $HOME && git clone https://github.com/google/googletest.git
    ```
    
    This creates the `$HOME/googletest` directory containing files from the GitHub repository.
    
2.  Create a directory for the build in the `googletest` directory.
    
    ```
    cd $HOME/googletest && mkdir build && cd build
    ```
    
3.  Run CMake from the `build` directory to generate the build files.
    
    ```
    cmake .. -DCMAKE_BUILD_TYPE=Release
    ```
    
4.  Run `make` to install GoogleTest.
    
    ```
    make
    ```
    
    If the builds succeed, you should see a `lib` directory in `$HOME/googletest/build` that contains the `libgtest.a` file.
    

SAM requires Google's [OR-Tools v9.14](https://github.com/google/or-tools/releases/tag/v9.14) for mixed-integer linear optimization.

1.  Download OR-Tools (v9.14) binaries for macOS from [GitHub assets](https://github.com/google/or-tools/releases/download/v9.14/or-tools_x86_64_macOS-15.5_cpp_v9.14.6206.tar.gz)
    
2.  Extract binaries files:
    

```
tar xvzf or-tools_x86_64_macOS-15.5_cpp_v9.14.6206.tar.gz
```

*   File name length can be a problem, if files are extracted in a deep directory.

SAM's build process assumes that directories for the code repositories are in the same directory.

```
mkdir $HOME/sam_dev
```

This example creates the `sam_dev` directory in your $HOME directory, but you can create it in a different directory or use a different name.

The four SAM code repositories are on GitHub.com:

*   [https://github.com/NREL/SAM/](https://github.com/NREL/SAM/)
*   [https://github.com/NREL/ssc/](https://github.com/NREL/ssc/)
*   [https://github.com/NREL/wex/](https://github.com/NREL/wex/)
*   [https://github.com/NREL/lk/](https://github.com/NREL/lk/)

Clone each repository into a separate directory in `$HOME/sam_dev`.

1.  Go to the directory you created for the SAM source code.
    
    ```
    cd $HOME/sam_dev
    ```
    
2.  Clone the repositories.
    
    ```
    for repo in lk wex ssc SAM ; do git clone https://github.com/nrel/$repo.git ; done
    ```
    
    This should create four folders in `$HOME/sam_dev`, each containing files downloaded from GitHub.com.
    

Depending on NLR's development schedule, by default `git clone` downloads either the `Develop` or `Patch` branch of each repository. The latest code is in the `Develop` branch. If you are contributing code, you should work with this branch. The code for the most recent version of SAM is in the `Patch` branch so `Develop` is likely to be ahead of `Patch`.

To build a specific version of SAM, you can check out a tag for that version. See [List of Tags for SAM Versions](https://github.com/NREL/SAM/wiki/List-of-Tags-for-SAM-Versions) for a list of tags for different versions of SAM, SSC, WEX and LK.

If you have access to the SAM-private repository to build offical NLR versions of SAM, clone it. You may need to use GitHub CLI (sudo apt install gh) to clone the private repository.

```
git clone https://github.com/NREL/SAM-private.git
```

The SAM build process use five environment variables to determine where the files it needs are stored on your computer. Before building SAM, set the following environment variables to point to each of the project folders.

To make these environment variables permanent, set them in your shell startup script (`$HOME/.zshrc` for zsh on newer macs or `$HOME/.bash_profile` for sh on older ones) and then close and reopen Terminal to update the environment variables. For example to use the nano text editor to open the shell startup script for zsh: `nano $HOME/.zshrc`.

```
export GTEST=$HOME/googletest
export LKDIR=$HOME/sam_dev/lk
export WEXDIR=$HOME/sam_dev/wex
export SSCDIR=$HOME/sam_dev/ssc
export SAMNTDIR=$HOME/sam_dev/SAM
export RAPIDJSONDIR=$HOME/sam_dev/ssc
export ORTOOLSDIR=$HOME/or-tools_x86_64_macOS-15.5_cpp_v9.14.6206
```

If you have access to the SAM-private repository and plan to build official NLR versions of SAM, set the environment variable for SAM-private:

```
export SAMNRELDIR=$HOME/sam_dev/SAM-private
```

To verify that the environment variables are set:

```
printenv
```

The CMakeLists.txt file contains instructions for CMake. Use a text editor to create `$HOME/sam_dev/CMakeLists.txt` and copy the following text into the file and save it:

```
cmake_minimum_required(VERSION 3.24)

set(CMAKE_OSX_DEPLOYMENT_TARGET "12" CACHE STRING "Minimum OS X deployment version")

if (UNIX AND NOT CMAKE_C_COMPILER)
    set(CMAKE_C_COMPILER gcc)
    set(CMAKE_CXX_COMPILER g++)
endif()

if(MSVC)
    set(CMAKE_CONFIGURATION_TYPES "Debug;Release;RelWithDebInfo" CACHE STRING "Debug and Release Builds Configured" FORCE)
endif()

Project(system_advisor_model CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(SAM_SKIP_TOOLS "Skips the SDKtool and TCSconsole builds" ON)
option(SAM_SKIP_TESTS "Skips building tests" ON)
option(SAMAPI_EXPORT "Exports of ssc binaries to the SAM_api directory; for Unix, also compiles ssc libraries for SAM_api. Required to build PySAM." OFF)
option(SAM_SKIP_AUTOGEN "Skips the generating SAMAPI files from export_config required for PySAM builds." ON) 

add_subdirectory(lk)
add_subdirectory(wex)
add_subdirectory(ssc)
add_subdirectory(SAM)
if (SAMPRIVATE)
    add_subdirectory(SAM-private)
    add_subdirectory(SAM-private/webupd)
endif()
```

The four CMake options control what projects are included in the build. The default options above are to build SAM without auxiliary tools tcsconsole and SDKtool and without generating files for [building the PySAM Python package](https://github.com/NREL/pysam/wiki/Building,-Packaging-and-Distributing). To minimize the time it takes for builds and to avoid build errors, use these default options unless you have a reason to change them.

The build folder contains executable and runtime files generated by the build process.

```
mkdir -p $HOME/sam_dev/build/Release
```

If you plan to debug SAM, create a separate directory for a Debug version:

```
 mkdir -p $HOME/sam_dev/build/Debug
```

If you are building SAM after changing environment variables, making code changes across different repositories, switching between GitHub branches, or other major changes, removing the existing build before starting a new one may prevent link and build errors.

```
rm -rf $HOME/sam_dev/build
```

Build SAM in XCode to use the XCode IDE to explore or modify SAM's source code, and to build SAM for both Intel and Apple architectures.

1.  Run CMake to generate an XCode project.
    
    For a Release build:
    
    ```
    cd $HOME/sam_dev/build/Release
    ```
    
    ```
    cmake ../.. -GXcode -T buildsystem=12 -DSAMAPI_EXPORT=0 -DSAM_SKIP_AUTOGEN=1 -DCMAKE_BUILD_TYPE="Release" "-DCMAKE_OSX_DEPLOYMENT_TARGET=12" "-DCMAKE_OSX_ARCHITECTURES=x86_64;arm64" -DCMAKE_XCODE_ATTRIBUTE_ONLY_ACTIVE_ARCH=NO -DCMAKE_SYSTEM_PREFIX_PATH=${ORTOOLSDIR} -Dabsl_DIR=${ORTOOLSDIR}\lib\cmake\absl" -Dutf8_range_DIR=${ORTOOLSDIR}\lib\cmake\utf8_range"
    ```
    
    For a Debug build, use `cd $HOME/sam_dev/build/Debug` and set `-DCMAKE_BUILD_TYPE="Debug"`.
    
    For a build of an official NLR version of SAM, use `-DSAM_SKIP_TOOLS=0` because the official NLR version's build process below requires SDKtool.
    
    CMake should create a `system_advisor_model.xcodeproj` file in the `$HOME/sam_dev/build/Release` directory, and if you built a Debug version, a separate `system_advisor_model.xcodeproj` file in the `$HOME/sam_dev/build/Debug` folder.
    
    If you are building SAM after changing environment variables, making code changes across different repositories, switching between GitHub branches, or other major changes, removing the XCode DerivedData folder before running `cmake` may prevent link and build errors.
    
    ```
    rm -rf $HOME/Library/Developer/Xcode/DerivedData/
    ```
    
2.  Start XCode and open the system\_advisor\_model project for either the Release or Debug build.
    
    ```
    open system_advisor_model.xcodeproj
    ```
    
3.  Choose the SAMOS scheme (SAMOSd for Debug builds): **Product, Scheme, Choose Scheme, SAMOS**.
    
4.  Choose the Release or Debug build configuration: **Product, Scheme, Edit Scheme, Info, Build Configuration, \[Debug/Release\]**.
    
    Be sure to choose the configuration that matches the project: A "Command PhaseScriptExecution failed with a nonzero exit code" error toward the end of the build may indicate that you chose the Debug configuration for the Release project or vice versa.
    
5.  Build the project: **Product, Build**.
    
    The build takes a few minutes. When the build finishes, you should see "Build Succeeded."
    
6.  Run SAM: **Product, Run**.
    

If you have access to the SAM-private repository to build official NLR versions, you can build SAM to test features specific to the official version such as weather file downloads and other API integrations, software registration, and updates.

1.  Build the open source version of SAM (SAMOS) in XCode as described above, but with the "Build for any Mac" option: **Product**, **Destination**, **Any Mac (x86\_64, arm64)**. _Do not use_ **Product**, **Run** _to build the project. Use_ **Product**, **Build** (⌘B) _instead._
    
2.  Also in Xcode, build SDKtool with "Build for any Mac" ⌘B. Be sure to edit the scheme to build either Release or Debug to match the SAMOS build.
    
3.  Use make to build SAM from SAM-private:
    
    ```
    cd path/to/SAM-private/build_osx
    ```
    
    ```
    make clean
    ```
    
    ```
    make setup
    ```
    
    ```
    make makes
    ```
    
    ```
    make app
    ```
    
4.  Run SAM:
    

SAM's Help system is HTML that opens in the computer's default web browser when you click **Help** or press the F1 key in the SAM user interface.

Important

The Safari web browser will only load CSS and Javascript elements from local files in developer mode. To display SAM Help correctly in Safari, go to Settings, Advanced Settings, and enable **Show features for web developers**.

Files to build SAM's Help system are in the `path/to/sam_dev/SAM/doc` folder. To build Help, run the Sphinx Python package to convert the source files to HTML, and then copy the HTML files to the `path/to/sam_dev/SAM/deploy/runtime/help/html` folder.

Building SAM's Help system requires:

*   Python
    
*   A virtual environment like `venv` or `conda` (recommended)
    
*   The Sphinx Python packages listed in `path/to/sam_dev/SAM/doc/requirements.txt`.
    
*   Make (optional)
    

For detailed build instructions and information about the Help system, see `path/to/sam_dev/SAM/doc/readme`.

1.  Go to the Help folder.
    
    ```
    cd path/to/sam_dev/SAM/doc
    ```
    
2.  Activate the virtual environment. For example, to activate a `venv` environment named "samdoc":
    
    ```
    source  path/to/venvs/samdoc/bin/activate
    ```
    
    If you need to create the virtual environment, run `python3 -m venv path/to/venvs/samdoc` to create the environment. The first time you activate the environment, install the required Python packages by running `pip install -r path/to/sam_dev/SAM/doc/requirements.txt`.
    
3.  Build Help.
    
    You can build Help by running Sphinx directly, or by using Make.
    
    To run Sphinx directly:
    
    ```
    sphinx-build -M html source build
    ```
    
    To use Make:
    
    ```
    make html
    ```
    
    To clean the build first, either delete the `path/to/sam_dev/SAM/doc/build` folder, or run `make clean`.
    
4.  Copy HTML files to deploy folder.
    
    Copy the entire contents of the `path/to/sam_dev/SAM/doc/build/html` folder to `path/to/sam_dev/SAM/deploy/runtime/help/html`. (Do not copy the `doc/build/doctrees` folder.)
    
    ```
    cp -R -f ./build/html ../deploy/runtime/help
    ```
    

The Welcome page of open-source builds of SAM displays "Please setup API keys, see private.h for details...". The `private.h` file contains credentials for several APIs used by NLR versions of SAM to access online databases such as for weather file downloads. It is not necessary to modifiy `private.h` to run and test SAM.

1.  When SAM starts, click **Start a new project**, and then click **Photovoltaic (detailed)** and **Residential (distributed)**, and **OK**.
    
2.  On the Location and Resource page, click **View data**. That should open a DView window with data from the weather file selected on the Location and Resource page. DView is from WEX, so that confirms that WEX built correctly.
    
3.  Close the DView window.
    
4.  Click through the input pages to see that they display correctly. The user interface uses libraries from wxWidgets and WEX.
    
5.  Click **Simulate** in the bottom left corner of the SAM window. SAM should run a simulation and display results on the Results page. The results page also uses DView from WEX, and displays data generated by SSC.
    
6.  Click **Macros** (under the **Simulate** button), and click the **Inverter Sizing Information** button. Click **Run macro** at the top of the window. The macro should run and display a window with information about the inverter's performance. That confirms that LK (also from WEX) is working.
    
7.  On any input page, click **Help** or press the F1 key to verify that the correct Help topic opens in the default web browser.
