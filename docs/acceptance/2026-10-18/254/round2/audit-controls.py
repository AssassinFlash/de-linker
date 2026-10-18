"""Repeat the scoped negative/positive audit control on c254 only.

Run from the c254 repository root after migration fixtures finish. Each run
uses its own customer and preserves other sessions' users. Report/MU paths
are fixed: run this control serially, never two copies concurrently.
The native fault filters apply only to that unique authenticated customer.
"""

from pathlib import Path
import json, subprocess, uuid
root=Path(__file__).resolve().parents[5]; assert str(root)=='/Users/chesterjohn/Documents/de-linker-worktrees/c254'
p=root/'docs/acceptance/2026-10-18/254'; out=p/'round2'; scratch=root/'.scratch/254-r2'
scratch.mkdir(parents=True,exist_ok=True)
wp=str(p/'wp-c254.sh'); cookie=scratch/'audit-cookie'; cookie_php=scratch/'audit-cookie.php'
def call(*args,**kw): return subprocess.run([wp,*args,'--user=1'],check=True,**kw)
cookie_php.write_text('''<?php
if ( wp_get_environment_type() !== 'local' || (int) wp_parse_url(home_url(),PHP_URL_PORT)!==9129 ) { throw new RuntimeException('c254 only'); }
$user=get_user_by('login','i254-visual');
if (!$user || !get_user_meta($user->ID,'_linker_254_visual_fixture',true)) { throw new RuntimeException('Owned fixture missing'); }
file_put_contents($args[0],LOGGED_IN_COOKIE.'='.wp_generate_auth_cookie($user->ID,time()+1200,'logged_in'));
''')
mu=Path('/Users/chesterjohn/de-linker-local/c254/wordpress/wp-content/mu-plugins/254-audit-fault.php')
assert not mu.exists()
login='i254-r2-audit-'+uuid.uuid4().hex[:8]
account=scratch/'audit-account.php';cleanup=scratch/'audit-cleanup.php'
account.write_text((p/'visual-account.php').read_text().replace('i254-visual',login).replace("'role' => 'customer',", "'role' => 'customer', 'meta_input' => array( '_linker_254_visual_fixture' => true ),"))
cleanup.write_text((p/'visual-cleanup.php').read_text().replace('i254-visual',login))
cookie_php.write_text(cookie_php.read_text().replace('i254-visual',login))
created=False
try:
 created=True
 call('eval-file',str(account),stdout=subprocess.DEVNULL)
 call('eval-file',str(cookie_php),str(cookie),stdout=subprocess.DEVNULL)
 mu.write_text(('''<?php
// Local negative control applies only to this run's unique owned customer.
if (wp_get_environment_type() !== 'local' || (int)wp_parse_url(home_url(),PHP_URL_PORT)!==9129) { return; }
add_filter('pll_rel_hreflang_attributes',static function($urls){
 if (wp_get_current_user()->user_login!=='__LOGIN__') { return $urls; }
 if (is_wc_endpoint_url('documents')) { return array(); }
 if (is_account_page() && isset($urls['de'])) { $urls['de']=home_url('/de/mein-konto/'); }
 return $urls;
},999);
add_filter('seopress_titles_canonical',static function($tag){return wp_get_current_user()->user_login==='__LOGIN__' && is_wc_endpoint_url('documents')?'':$tag;},999);
''').replace('__LOGIN__',login))
 with (out/'audit-negative.log').open('w') as log:
  bad=subprocess.run(['python3',str(p/'audit.py'),'--cookie-file',str(cookie),'--output',str(out/'audit-negative-full.json')],stdout=log,stderr=subprocess.STDOUT)
 report=json.loads((out/'audit-negative-full.json').read_text()); defects=report['defects']
 assert bad.returncode!=0, 'Audit accepted intentionally broken metadata'
 assert any('German alternate is not the final address' in d and 'mein-konto' in d for d in defects),defects
 assert any('Canonical is not the final address' in d and 'mein-konto/dokumente/' in d for d in defects),defects
 (out/'audit-negative.json').write_text(json.dumps({'exit_code':bad.returncode,'defects':defects,'injection':"Native filters scoped to this run's unique authenticated customer: account alternate to root; documents canonical and hreflang omitted. Other sessions are unaffected.",'cleanup':'Temporary MU removed in finally before positive audit.'},ensure_ascii=False,indent=2)+'\n')
 mu.unlink()
 with (out/'audit-green.log').open('w') as log:
  subprocess.run(['python3',str(p/'audit.py'),'--cookie-file',str(cookie),'--output',str(out/'route-results.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
 try:
  mu.unlink(missing_ok=True)
 finally:
  try:
   if created: call('eval-file',str(cleanup),stdout=subprocess.DEVNULL)
  finally:
   cookie.unlink(missing_ok=True)
print('Strict public audit negative control rejected; full real audit passed; fixture removed.',flush=True)
