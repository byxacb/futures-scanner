#!/usr/bin/env python3
"""生成 Xcode 项目文件

运行方式：cd FuturesBot && python3 setup_project.py
然后用 Xcode 打开 FuturesBot.xcodeproj
"""

import os
import uuid
import hashlib

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_DIR, "FuturesBot")

# 收集所有 Swift 文件
def find_swift_files():
    files = []
    for root, dirs, fnames in os.walk(SRC_DIR):
        for f in sorted(fnames):
            if f.endswith(".swift"):
                rel = os.path.relpath(os.path.join(root, f), PROJECT_DIR)
                files.append(rel)
    return files

# 生成确定性 UUID
def make_uuid(name):
    h = hashlib.md5(name.encode()).hexdigest()[:24].upper()
    return h

def generate_pbxproj(files):
    # 为每个文件生成 UUID
    file_uuids = {}
    group_uuids = {}
    for f in files:
        file_uuids[f] = make_uuid(f"file_{f}")
        group_uuids[f] = make_uuid(f"group_{os.path.dirname(f)}")

    root_uuid = make_uuid("root")
    main_group = make_uuid("main_group")
    src_group = make_uuid("src_group")
    products_group = make_uuid("products_group")
    frameworks_group = make_uuid("frameworks_group")
    app_target = make_uuid("app_target")
    app_product = make_uuid("app_product")
    build_config_list = make_uuid("build_config_list")
    debug_config = make_uuid("debug_config")
    release_config = make_uuid("release_config")
    project_uuid = make_uuid("project")

    # 收集所有 group
    all_dirs = set()
    for f in files:
        d = os.path.dirname(f)
        while d:
            all_dirs.add(d)
            d = os.path.dirname(d)

    # Build file refs
    build_file_refs = []
    file_refs = []
    for f in files:
        uid = file_uuids[f]
        build_file_refs.append(f'\t\t{uid} /* {os.path.basename(f)} in Sources */ = {{isa = PBXBuildFile; fileRef = {uid} /* {os.path.basename(f)} */; }};')
        file_refs.append(f'\t\t{uid} /* {os.path.basename(f)} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {os.path.basename(f)}; sourceTree = "<group>"; }};')

    # Group refs
    group_refs = []
    for d in sorted(all_dirs, key=lambda x: x.count('/')):
        uid = group_uuids.get(d)
        if not uid:
            continue
        name = os.path.basename(d)
        # 找子文件
        children = []
        for f in files:
            if os.path.dirname(f) == d:
                children.append(f'{file_uuids[f]} /* {os.path.basename(f)} */')
        for sd in all_dirs:
            if os.path.dirname(sd) == d and sd in group_uuids:
                children.append(f'{group_uuids[sd]} /* {os.path.basename(sd)} */')
        children_str = ",\n".join(sorted(children))
        group_refs.append(f'\t\t{uid} /* {name} */ = {{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = (\n{children_str},\n\t\t\t);\n\t\t\tpath = {name};\n\t\t\tsourceTree = "<group>";\n\t\t}};')

    # Root group children
    root_children = []
    if "" in group_uuids:
        root_children.append(group_uuids[""] + " /* FuturesBot */")
    root_children.append(products_group + " /* Products */")
    root_children.append(frameworks_group + " /* Frameworks */")

    # Top-level group (FuturesBot/)
    top_children = []
    for d in sorted(all_dirs):
        if '/' not in d and d != "":
            top_children.append(group_uuids[d] + " /* " + os.path.basename(d) + " */")
    for f in files:
        if '/' not in os.path.dirname(f):
            top_children.append(file_uuids[f] + " /* " + os.path.basename(f) + " */")

    top_children_str = ",\n".join(sorted(top_children))

    root_children_str = ",\n".join(root_children)

    # Build files list
    build_files_str = ",\n".join(sorted(build_file_refs))

    pbxproj = f"""// !$*UTF8*$!
{{
\tarchiveVersion = 1;
\tclasses = {{
\t}};
\tobjectVersion = 56;
\tobjects = {{

/* Begin PBXBuildFile section */
{build_files_str}
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
{chr(10).join(sorted(file_refs))}
\t\t{app_product} /* FuturesBot.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = FuturesBot.app; sourceTree = BUILT_PRODUCTS_DIR; }};
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
\t\t{make_uuid("frameworks_phase")} /* Frameworks */ = {{
\t\t\tisa = PBXFrameworksBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
\t\t{main_group} = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{root_children_str},
\t\t\t);
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{products_group} /* Products */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t\t{app_product} /* FuturesBot.app */,
\t\t\t);
\t\t\tname = Products;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{frameworks_group} /* Frameworks */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t);
\t\t\tname = Frameworks;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{group_uuids.get("", make_uuid("empty"))} /* FuturesBot */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{top_children_str},
\t\t\t);
\t\t\tpath = FuturesBot;
\t\t\tsourceTree = "<group>";
\t\t}};
{chr(10).join(group_refs)}
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
\t\t{app_target} /* FuturesBot */ = {{
\t\t\tisa = PBXNativeTarget;
\t\t\tbuildConfigurationList = {build_config_list} /* Build configuration list for PBXNativeTarget "FuturesBot" */;
\t\t\tbuildPhases = (
\t\t\t\t{make_uuid("sources_phase")} /* Sources */,
\t\t\t\t{make_uuid("frameworks_phase")} /* Frameworks */,
\t\t\t\t{make_uuid("resources_phase")} /* Resources */,
\t\t\t);
\t\t\tbuildRules = (
\t\t\t);
\t\t\tdependencies = (
\t\t\t);
\t\t\tname = FuturesBot;
\t\t\tproductName = FuturesBot;
\t\t\tproductReference = {app_product} /* FuturesBot.app */;
\t\t\tproductType = "com.apple.product-type.application";
\t\t}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
\t\t{project_uuid} /* Project object */ = {{
\t\t\tisa = PBXProject;
\t\t\tattributes = {{
\t\t\t\tBuildIndependentTargetsInParallel = 1;
\t\t\t\tLastSwiftUpdateCheck = 1540;
\t\t\t\tLastUpgradeCheck = 1540;
\t\t\t}};
\t\t\tbuildConfigurationList = {make_uuid("project_config")} /* Build configuration list for PBXProject "FuturesBot" */;
\t\t\tcompatibilityVersion = "Xcode 14.0";
\t\t\tdevelopmentRegion = "zh-Hans";
\t\t\thasScannedForEncodings = 0;
\t\t\tknownRegions = (
\t\t\t\t"zh-Hans",
\t\t\t\tBase,
\t\t\t);
\t\t\tmainGroup = {main_group};
\t\t\tproductRefGroup = {products_group} /* Products */;
\t\t\tprojectDirPath = "";
\t\t\tprojectRoot = "";
\t\t\ttargets = (
\t\t\t\t{app_target} /* FuturesBot */,
\t\t\t);
\t\t}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
\t\t{make_uuid("resources_phase")} /* Resources */ = {{
\t\t\tisa = PBXResourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
\t\t{make_uuid("sources_phase")} /* Sources */ = {{
\t\t\tisa = PBXSourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
{build_files_str}
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
\t\t{debug_config} /* Debug */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
\t\t\t\tASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
\t\t\t\tCODE_SIGN_STYLE = Automatic;
\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = FuturesBot;
\t\t\t\tINFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
\t\t\t\tINFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;
\t\t\t\tINFOPLIST_KEY_UILaunchScreen_Generation = YES;
\t\t\t\tINFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = "UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
\t\t\t\tINFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = "UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (
\t\t\t\t\t"$(inherited)",
\t\t\t\t\t"@executable_path/Frameworks",
\t\t\t\t);
\t\t\t\tMARKETING_VERSION = 1.0;
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.futuresbot.app;
\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";
\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;
\t\t\t\tSWIFT_VERSION = 5.0;
\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";
\t\t\t}};
\t\t\tname = Debug;
\t\t}};
\t\t{release_config} /* Release */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
\t\t\t\tASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
\t\t\t\tCODE_SIGN_STYLE = Automatic;
\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = FuturesBot;
\t\t\t\tINFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
\t\t\t\tINFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;
\t\t\t\tINFOPLIST_KEY_UILaunchScreen_Generation = YES;
\t\t\t\tINFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = "UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
\t\t\t\tINFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = "UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (
\t\t\t\t\t"$(inherited)",
\t\t\t\t\t"@executable_path/Frameworks",
\t\t\t\t);
\t\t\t\tMARKETING_VERSION = 1.0;
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.futuresbot.app;
\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";
\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;
\t\t\t\tSWIFT_VERSION = 5.0;
\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";
\t\t\t}};
\t\t\tname = Release;
\t\t}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
\t\t{build_config_list} /* Build configuration list for PBXNativeTarget "FuturesBot" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{debug_config} /* Debug */,
\t\t\t\t{release_config} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
\t\t{make_uuid("project_config")} /* Build configuration list for PBXProject "FuturesBot" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{make_uuid("project_debug")} /* Debug */,
\t\t\t\t{make_uuid("project_release")} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
/* End XCConfigurationList section */

\t};
\trootObject = {project_uuid} /* Project object */;
}}
"""
    return pbxproj


def main():
    files = find_swift_files()
    print(f"找到 {len(files)} 个 Swift 文件:")
    for f in files:
        print(f"  {f}")

    # 创建 .xcodeproj 目录
    xcodeproj = os.path.join(PROJECT_DIR, "FuturesBot.xcodeproj")
    os.makedirs(xcodeproj, exist_ok=True)

    # 写 project.pbxproj
    pbxproj_path = os.path.join(xcodeproj, "project.pbxproj")
    with open(pbxproj_path, 'w', encoding='utf-8') as f:
        f.write(generate_pbxproj(files))

    print(f"\n✅ Xcode 项目已生成: {xcodeproj}")
    print("   用 Xcode 打开 FuturesBot.xcodeproj 即可编译运行")


if __name__ == "__main__":
    main()
