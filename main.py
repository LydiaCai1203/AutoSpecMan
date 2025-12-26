from detector.structure_detector import StructureDetector
from detector.codestyle_detector import CodeStyleDetector
from detector.versioncontrol_detector import VersionControlDetector
from detector.api_design_detector import ApiDesignDetector

if __name__ == "__main__":
    # 结构检测
    # detector = StructureDetector(
    #     config_path="/Users/caiqj/project/private/new/AutoSpecMan/config/config.yaml",
    #     config_type="structure"
    # )
    # detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/structure.md")

    # 代码风格检测
    # detector = CodeStyleDetector(
    #     config_path="/Users/caiqj/project/private/new/AutoSpecMan/config/config.yaml",
    #     config_type="codestyle"
    # )
    # detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/code_style.md")

    # 版本控制习惯检测
    # detector = VersionControlDetector(
    #     config_path="/Users/caiqj/project/private/new/AutoSpecMan/config/config.yaml",
    #     config_type="git"
    # )
    # detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/version_control.md")

    # API 设计规范检测
    detector = ApiDesignDetector(
        config_path="/Users/caiqj/project/private/new/AutoSpecMan/config/config.yaml",
        config_type="api"
    )
    detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/api_design.md")