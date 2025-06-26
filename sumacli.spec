#
# spec file for package sumacli
#
# Copyright (c) 2024 Geronimo Poppino <gpoppino@outlook.com>
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

Name:           sumacli
Version:        1.0.0
Release:        0
Summary:        Schedules SUSE-Manager clients for patching, migration or upgrade from the CLI
License:        GPL-3.0-or-later
Group:          Applications/System
URL:            https://github.com/gpoppino/sumacli
Source:         https://github.com/gpoppino/sumacli/releases/download/v%{version}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch
BuildRequires:  python311
BuildRequires:  python-rpm-macros
Requires:       python311

%description
Schedules SUSE-Manager clients for patching, migration or upgrade from the CLI

%prep
%setup -q

%build
# nothing to build

%install
%{__mkdir_p} %{buildroot}/%{_bindir}

%if 0%{suse_version}
    sed -i 's|#!/usr/bin/python3|#!/usr/bin/python3.11|' ./src/sumacli/main.py
%endif
%{__install} -p -m0755 src/__main__.py %{buildroot}/%{_bindir}/sumacli

%{__mkdir_p} %{buildroot}/%{_sysconfdir}/sumacli
%{__install} -p -m0644 src/sumacli/conf/logging.conf %{buildroot}/%{_sysconfdir}/sumacli/

%{__mkdir_p} %{buildroot}/%{python311_sitelib}/sumacli
%{__install} -p -m0644 src/sumacli/*.py %{buildroot}/%{python311_sitelib}/sumacli/

touch %{buildroot}/%{python311_sitelib}/sumacli/__init__.py
%{__chmod} 0644 %{buildroot}/%{python311_sitelib}/sumacli/__init__.py

%python311_compile

%files
%defattr(-,root,root)
%{_bindir}/sumacli
%{python311_sitelib}/sumacli/
%config %{_sysconfdir}/sumacli/logging.conf

%changelog
