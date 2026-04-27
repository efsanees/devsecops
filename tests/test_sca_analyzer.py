"""Unit testler — app/security/sca_analyzer.py (ağsız)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.security.sca_analyzer import (
    _parse_requirements,
    _parse_package_json,
    _parse_csproj,
    _parse_pom_xml,
    _parse_go_mod,
    _parse_cargo_lock,
    _severity_from_cvss,
    _extract_fixed_version,
    _find_all,
)


class TestParseRequirements:
    def test_basic_pin(self):
        content = "Django==3.2.0\nrequests>=2.20\nflask~=2.0.1\n"
        pkgs = _parse_requirements(content)
        names = [p["name"] for p in pkgs]
        assert "Django" in names and "requests" in names and "flask" in names

    def test_django_version(self):
        pkgs = _parse_requirements("Django==3.2.0")
        assert pkgs[0]["version"] == "3.2.0"

    def test_ignore_comments_and_flags(self):
        content = "# comment\n-r base.txt\ngit+https://github.com/foo/bar\nrequests\n"
        pkgs = _parse_requirements(content)
        assert len(pkgs) == 1 and pkgs[0]["name"] == "requests"

    def test_no_version(self):
        pkgs = _parse_requirements("pyyaml")
        assert pkgs[0]["name"] == "pyyaml"
        assert pkgs[0]["version"] == ""

    def test_extras(self):
        pkgs = _parse_requirements("uvicorn[standard]==0.20.0")
        assert pkgs[0]["name"] == "uvicorn[standard]"
        assert pkgs[0]["version"] == "0.20.0"

    def test_empty_file(self):
        assert _parse_requirements("") == []
        assert _parse_requirements("# only comments") == []


class TestParsePackageJson:
    def test_basic(self):
        content = '{"dependencies":{"express":"^4.18.0"},"devDependencies":{"jest":"29.0.0"}}'
        pkgs = _parse_package_json(content)
        names = [p["name"] for p in pkgs]
        assert "express" in names and "jest" in names

    def test_version_strip(self):
        pkgs = _parse_package_json('{"dependencies":{"lodash":"~4.17.21"}}')
        assert pkgs[0]["version"] == "4.17.21"

    def test_caret_strip(self):
        pkgs = _parse_package_json('{"dependencies":{"axios":"^1.6.0"}}')
        assert pkgs[0]["version"] == "1.6.0"

    def test_invalid_json(self):
        assert _parse_package_json("not json") == []

    def test_empty_deps(self):
        assert _parse_package_json('{"name":"foo"}') == []


class TestParseCsproj:
    def test_basic_package_reference(self):
        xml = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
    <PackageReference Include="Microsoft.AspNetCore.App" Version="2.2.0" />
  </ItemGroup>
</Project>"""
        pkgs = _parse_csproj(xml)
        names = [p["name"] for p in pkgs]
        assert "Newtonsoft.Json" in names
        assert "Microsoft.AspNetCore.App" in names

    def test_version_captured(self):
        xml = '<Project><ItemGroup><PackageReference Include="Serilog" Version="3.1.1" /></ItemGroup></Project>'
        pkgs = _parse_csproj(xml)
        assert pkgs[0]["version"] == "3.1.1"

    def test_version_as_child_element(self):
        xml = """<Project>
  <ItemGroup>
    <PackageReference Include="NUnit">
      <Version>3.13.3</Version>
    </PackageReference>
  </ItemGroup>
</Project>"""
        pkgs = _parse_csproj(xml)
        assert pkgs[0]["name"] == "NUnit"
        assert pkgs[0]["version"] == "3.13.3"

    def test_empty_project(self):
        xml = '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup></PropertyGroup></Project>'
        assert _parse_csproj(xml) == []

    def test_invalid_xml(self):
        assert _parse_csproj("not xml at all") == []


class TestParsePomXml:
    def test_basic_dependency(self):
        xml = """<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>5.3.0</version>
    </dependency>
  </dependencies>
</project>"""
        pkgs = _parse_pom_xml(xml)
        assert pkgs[0]["name"] == "org.springframework:spring-core"
        assert pkgs[0]["version"] == "5.3.0"

    def test_multiple_deps(self):
        xml = """<project>
  <dependencies>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.14.0</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
    </dependency>
  </dependencies>
</project>"""
        pkgs = _parse_pom_xml(xml)
        assert len(pkgs) == 2

    def test_dynamic_version_skipped(self):
        xml = """<project>
  <dependencies>
    <dependency>
      <groupId>org.foo</groupId>
      <artifactId>bar</artifactId>
      <version>${foo.version}</version>
    </dependency>
  </dependencies>
</project>"""
        pkgs = _parse_pom_xml(xml)
        assert pkgs[0]["version"] == ""

    def test_namespace_handled(self):
        xml = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency>
      <groupId>org.test</groupId>
      <artifactId>lib</artifactId>
      <version>1.0.0</version>
    </dependency>
  </dependencies>
</project>"""
        pkgs = _parse_pom_xml(xml)
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "org.test:lib"

    def test_invalid_xml(self):
        assert _parse_pom_xml("not xml") == []


class TestParseGoMod:
    def test_block_require(self):
        content = """module example.com/app

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
    golang.org/x/net v0.17.0 // indirect
)
"""
        pkgs = _parse_go_mod(content)
        names = [p["name"] for p in pkgs]
        assert "github.com/gin-gonic/gin" in names
        assert "golang.org/x/net" in names

    def test_single_require(self):
        content = "module foo\nrequire github.com/sirupsen/logrus v1.9.3\n"
        pkgs = _parse_go_mod(content)
        assert pkgs[0]["name"] == "github.com/sirupsen/logrus"
        assert pkgs[0]["version"] == "v1.9.3"

    def test_version_preserved(self):
        content = "require (\n    github.com/foo/bar v2.1.0\n)\n"
        pkgs = _parse_go_mod(content)
        assert pkgs[0]["version"] == "v2.1.0"

    def test_empty(self):
        assert _parse_go_mod("module foo\ngo 1.21\n") == []


class TestParseCargoLock:
    def test_basic(self):
        content = """# This file is automatically @generated
[[package]]
name = "serde"
version = "1.0.193"

[[package]]
name = "tokio"
version = "1.35.1"
"""
        pkgs = _parse_cargo_lock(content)
        names = [p["name"] for p in pkgs]
        assert "serde" in names and "tokio" in names

    def test_version_captured(self):
        content = '[[package]]\nname = "rand"\nversion = "0.8.5"\n'
        pkgs = _parse_cargo_lock(content)
        assert pkgs[0]["version"] == "0.8.5"

    def test_empty(self):
        assert _parse_cargo_lock("") == []

    def test_no_version(self):
        content = '[[package]]\nname = "mylib"\n'
        pkgs = _parse_cargo_lock(content)
        assert pkgs[0]["name"] == "mylib"
        assert pkgs[0]["version"] == ""


class TestSeverityFromCvss:
    def test_critical(self):
        assert _severity_from_cvss(9.5) == "CRITICAL"

    def test_high(self):
        assert _severity_from_cvss(7.5) == "HIGH"

    def test_medium(self):
        assert _severity_from_cvss(5.0) == "MEDIUM"

    def test_low(self):
        assert _severity_from_cvss(2.0) == "LOW"


class TestExtractFixedVersion:
    def test_finds_fixed(self):
        vuln = {"affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.2.3"}]}]}]}
        assert _extract_fixed_version(vuln) == "1.2.3"

    def test_no_fixed(self):
        vuln = {"affected": [{"ranges": [{"events": [{"introduced": "0"}]}]}]}
        assert _extract_fixed_version(vuln) == "bilinmiyor"

    def test_empty(self):
        assert _extract_fixed_version({}) == "bilinmiyor"


class TestFindAll:
    def test_finds_csproj(self):
        files = ["src/App.csproj", "tests/App.Tests.csproj", "README.md"]
        result = _find_all(files, ".csproj")
        assert len(result) == 2
        assert "src/App.csproj" in result

    def test_no_match(self):
        assert _find_all(["foo.py", "bar.js"], ".csproj") == []
