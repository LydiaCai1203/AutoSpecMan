from detector.structure_detector import StructureDetector
from detector.codestyle_detector import CodeStyleDetector

if __name__ == "__main__":
    # 结构检测
    # detector = StructureDetector(
    #     config_path="/Users/caiqj/project/private/new/AutoSpecMan/config/config.yaml",
    #     config_type="structure"
    # )
    # detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/structure.md")

    # 代码风格检测 - 直接传入 config，自动转换
    detector = CodeStyleDetector(
        config_path="/Users/caiqj/project/private/new/AutoSpecMan/config/config.yaml",
        config_type="codestyle"
    )
    detector.detect_to_file(output_path="/Users/caiqj/project/private/new/AutoSpecMan/result/code_style.md")