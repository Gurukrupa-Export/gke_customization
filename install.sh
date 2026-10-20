#!/bin/bash
set -e

cd ~ || exit

echo "::group::Install Bench"
pip install --upgrade pip
pip install uv frappe-bench
echo "::endgroup::"

echo "::group::Init Bench"
bench init frappe-bench \
    --frappe-branch version-16 \
    --skip-assets \
    --python "$(which python)"

cd frappe-bench || exit
echo "::endgroup::"

echo "::group::Get Apps"

bench get-app erpnext --branch version-16
bench get-app hrms --branch version-16
bench get-app payments --branch develop
bench get-app lending --branch version-16-beta
bench get-app wiki --branch version-3
bench get-app helpdesk --branch main --skip-assets
bench get-app telephony --branch develop

bench get-app https://github.com/resilient-tech/india-compliance.git --branch version-16
bench get-app https://github.com/Gurukrupa-Export/jewellery-erpnext.git --branch kggk_uat
bench get-app https://github.com/Gurukrupa-Export/gurukrupa_biometric.git --branch master
bench get-app https://github.com/Gurukrupa-Export/gurukrupa_customizations.git --branch main

echo "::endgroup::"

echo "::group::Install PR Branch App"
bench get-app file://$GITHUB_WORKSPACE
echo "::endgroup::"

echo "::group::Verify Apps"
bench list-apps
ls -la apps/
echo "::endgroup::"

echo "::group::Configure Redis"

bench set-config -g redis_cache redis://127.0.0.1:6379
bench set-config -g redis_queue redis://127.0.0.1:6379
bench set-config -g redis_socketio redis://127.0.0.1:6379

echo "::endgroup::"

echo "::group::Create Site"

bench new-site test_site \
    --admin-password admin \
    --db-root-password travis \
    --mariadb-root-username root \
    --no-mariadb-socket

echo "::endgroup::"

echo "::group::Enable Server Scripts"

bench set-config -g server_script_enabled true
bench --site test_site set-config server_script_enabled 1

echo "::endgroup::"

echo "::group::Copying fixtures from git_action_v16..."
echo "Workspace = $GITHUB_WORKSPACE"
ls -la "$GITHUB_WORKSPACE/fixture_source"

ls -la "$GITHUB_WORKSPACE/fixture_source/jewellery_erpnext"

find "$GITHUB_WORKSPACE/fixture_source" -type d -name fixtures

cp -rf \
"$GITHUB_WORKSPACE/fixture_source/jewellery_erpnext/fixtures/"* \
"$HOME/frappe-bench/apps/jewellery_erpnext/jewellery_erpnext/fixtures/"
echo "::endgroup::"

echo "::group::Install Apps"

echo "Disabling gke_customization fixtures..."

mv \
    apps/gke_customization/gke_customization/fixtures \
    apps/gke_customization/gke_customization/fixtures_disabled

bench --site test_site install-app erpnext
bench --site test_site install-app hrms
bench --site test_site install-app payments
bench --site test_site install-app india_compliance
bench --site test_site install-app lending
bench --site test_site install-app wiki
bench --site test_site install-app telephony
bench --site test_site install-app helpdesk

bench --site test_site install-app jewellery_erpnext
bench --site test_site install-app gke_customization
bench --site test_site install-app gurukrupa_biometric
bench --site test_site install-app gurukrupa_customizations

echo "::endgroup::"
