// Synthetic end-to-end verification of the actual Next.js API rewrite.
// Does NOT contact Instagram, Supabase, production Raspberry or real accounts.
const assert=require('node:assert/strict');
const http=require('node:http');
const {spawn}=require('node:child_process');
const {chromium}=require('playwright-core');

const upstreamHost='127.0.0.1',upstreamPort=19999,webPort=13101;
const account={
 id:'11111111-1111-4111-8111-111111111111',email:'qa-user@example.com',
 first_name:'Synthetic',last_name:'Owner',is_active:true,last_login_at:null,
 memberships:[{workspace_id:'22222222-2222-4222-8222-222222222222',
 workspace_name:'Synthetic QA',workspace_slug:'qa',role:'OWNER',currency_code:'UAH'}]
};
const counts={login:0,refresh:0,profile:0,logout:0};
const cookieName='sellora_session_refresh';
let issued=0,session=null;
function json(res,status,body,headers={}){
 res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store',...headers});
 res.end(JSON.stringify(body));
}
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost');
 const path=url.pathname.replace(/^\/api\/v1/,'');
 const cookie=req.headers.cookie||'';
 if(path==='/auth/session/login'&&req.method==='POST'){
  counts.login++;session='synthetic-refresh-'+(++issued);
  return json(res,200,{access_token:'synthetic-access',token_type:'bearer'},{
   'Set-Cookie':cookieName+'='+session+'; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/session; Max-Age=1200'
  });
 }
 if(path==='/auth/session/refresh'&&req.method==='POST'){
  counts.refresh++;
  if(!session||!cookie.split('; ').includes(cookieName+'='+session))return json(res,401,{detail:'No valid session'});
  session='synthetic-refresh-'+(++issued);
  return json(res,200,{access_token:'synthetic-new-access',token_type:'bearer'},{
   'Set-Cookie':cookieName+'='+session+'; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/session; Max-Age=1200'
  });
 }
 if(path==='/auth/session/logout'&&req.method==='POST'){
  counts.logout++;session=null;
  res.writeHead(204,{'Set-Cookie':cookieName+'=; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/session; Max-Age=0','Cache-Control':'no-store'});
  return res.end();
 }
 if(path==='/auth/me'){
  counts.profile++;
  if(!req.headers.authorization?.startsWith('Bearer synthetic-'))return json(res,401,{detail:'No access token'});
  return json(res,200,account);
 }
 if(path.startsWith('/auth/session'))return json(res,404,{detail:'Not configured'});
 return json(res,200,{});
});
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let browser,app;
async function main(){
 await new Promise(resolve=>server.listen(upstreamPort,upstreamHost,resolve));
 app=spawn('npm',['--prefix','frontend','run','start','--','--hostname','127.0.0.1','--port',String(webPort)],{
   env:{...process.env,NEXT_PUBLIC_COOKIE_SESSION_AUTH_ENABLED:'true',
   SELLORA_API_UPSTREAM_URL:'http://127.0.0.1:'+upstreamPort},
   stdio:['ignore','pipe','pipe']
 });
 let stderr='';
 app.stderr.on('data',chunk=>stderr+=String(chunk).slice(-500));
 const base='http://localhost:'+webPort;
 let up=false;
 for(let i=0;i<80;i++){
  try{const response=await fetch(base+'/login');if(response.ok){up=true;break;}}catch{}
  await sleep(400);
 }
 assert.ok(up,'Next.js QA server did not start '+stderr.slice(-350));
 browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844}});
 const page=await context.newPage();
 const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
 // First load must remain unauthenticated; the stub returns 401 if cookie absent.
 await page.locator('input[type="email"]').fill(account.email);
 await page.locator('input[type="password"]').fill('synthetic-no-real-password');
 await page.locator('button[type="submit"]').click();
 await page.waitForURL(/\/dashboard/,{timeout:20000});
 assert.equal(counts.login,1);
 let cookies=await context.cookies(base);
 let refreshCookie=cookies.find(c=>c.name===cookieName);
 assert.ok(refreshCookie,'Next.js rewrite dropped Set-Cookie');
 assert.equal(refreshCookie.httpOnly,true,'Cookie is accessible to JavaScript');
 assert.equal(refreshCookie.secure,true,'Cookie is not Secure');
 assert.equal(refreshCookie.sameSite,'Lax');
 assert.equal(refreshCookie.path,'/api/v1/auth/session');
 let keys=await page.evaluate(()=>Object.keys(localStorage).filter(k=>/access_token|refresh_token|current_user/.test(k)));
 assert.deepEqual(keys,[]);
 await page.reload({waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.location.pathname==='/dashboard',{timeout:16000});
 assert.ok(counts.refresh>=1,'Browser did not forward HttpOnly cookie through Next.js rewrite');
 keys=await page.evaluate(()=>Object.keys(localStorage).filter(k=>/access_token|refresh_token|current_user/.test(k)));
 assert.deepEqual(keys,[]);
 cookies=await context.cookies(base);
 refreshCookie=cookies.find(c=>c.name===cookieName);
 assert.ok(refreshCookie&&refreshCookie.value!== 'synthetic-refresh-1','Rotated Set-Cookie was not forwarded');
 const authErrors=errors.filter(e=>/auth|session|refresh|token|cookie/i.test(e));
 assert.deepEqual(authErrors,[]);
 // Browser must never expose the HttpOnly credential to document.cookie.
 const visible=await page.evaluate(()=>document.cookie);
 assert.ok(!visible.includes(cookieName),'HttpOnly cookie visible to JS');
 console.log(JSON.stringify({result:'COOKIE_REWRITE_PASS',chrome:'Google Chrome',viewport:'390x844',
 proxyPath:'/api/v1',login:counts.login,refresh:counts.refresh,profile:counts.profile,
 cookie:{httpOnly:refreshCookie.httpOnly,secure:refreshCookie.secure,
 sameSite:refreshCookie.sameSite,path:refreshCookie.path},
 localStorageTokens:keys.length,visibleCookie:false,authErrors:0,
 unrelatedSyntheticDashboardErrors:errors.length}));
}
main().catch(err=>{console.error('COOKIE_REWRITE_SMOKE_FAILED',err.stack);process.exitCode=1;}).finally(async()=>{
 if(browser)await browser.close().catch(()=>{});
 if(app)app.kill('SIGTERM');
 await new Promise(resolve=>server.close(resolve));
 process.exit(process.exitCode||0);
});
