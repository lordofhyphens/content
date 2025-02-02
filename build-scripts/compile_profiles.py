from __future__ import print_function

import argparse
import logging
import sys
import os.path
from glob import glob

import ssg.build_yaml
import ssg.controls

def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile_file", nargs="*")
    parser.add_argument(
        "--build-config-yaml",
        help="YAML file with information about the build configuration. "
        "e.g.: ~/scap-security-guide/build/build_config.yml "
        "needed for autodetection of profile root"
    )
    parser.add_argument(
        "--product-yaml",
        help="YAML file with information about the product we are building. "
        "e.g.: ~/scap-security-guide/rhel7/product.yml "
        "needed for autodetection of profile root"
    )
    parser.add_argument(
        "--output", "-o", default="{name}.profile",
        help="The template for saving processed profile files."
    )
    parser.add_argument(
        "--controls-dir",
        help="Directory that contains control files with policy controls. "
        "e.g.: ~/scap-security-guide/controls",
    )
    return parser


def make_name_to_profile_mapping(profile_files, env_yaml):
    name_to_profile = {}
    for f in profile_files:
        try:
            p = ssg.build_yaml.ProfileWithInlinePolicies.from_yaml(f, env_yaml)
            name_to_profile[p.id_] = p
        except Exception as exc:
            # The profile is probably doc-incomplete
            msg = "Not building profile from {fname}: {err}".format(
                fname=f, err=str(exc))
            print(msg, file=sys.stderr)
    return name_to_profile


def get_env_yaml(build_config_yaml, product_yaml):
    if build_config_yaml is None or product_yaml is None:
        return None

    env_yaml = ssg.environment.open_environment(build_config_yaml, product_yaml)
    return env_yaml


def get_profile_files_from_root(env_yaml, product_yaml):
    profile_files = []
    if env_yaml:
        base_dir = os.path.dirname(product_yaml)
        profiles_root = ssg.utils.required_key(env_yaml, "profiles_root")
        profile_files = sorted(glob("{base_dir}/{profiles_root}/*.profile"
                             .format(profiles_root=profiles_root, base_dir=base_dir)))
    return profile_files


def main():
    parser = create_parser()
    args = parser.parse_args()
    env_yaml = get_env_yaml(args.build_config_yaml, args.product_yaml)

    build_root = os.path.dirname(args.build_config_yaml)

    logfile = "{build_root}/{product}/control_profiles.log".format(
            build_root=build_root,
            product=env_yaml["product"])
    logging.basicConfig(filename=logfile, level=logging.INFO)

    if args.controls_dir:
        controls_manager = ssg.controls.ControlsManager(args.controls_dir, env_yaml)
        controls_manager.load()

    profile_files = get_profile_files_from_root(env_yaml, args.product_yaml)
    profile_files.extend(args.profile_file)
    profiles = make_name_to_profile_mapping(profile_files, env_yaml)
    for pname in profiles:
        profiles[pname].resolve(profiles, controls_manager)

    for name, p in profiles.items():
        p.dump_yaml(args.output.format(name=name))


if __name__ == "__main__":
    main()
