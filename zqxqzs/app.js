// PWA Service Worker
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');

// ============ DATA ============
const ALL_PRODUCTS = ['专线','短彩信','千里眼','云视讯','和对讲','和车队','移动云','物联网'];
const SUB_OPTS = {
  '和对讲': {L1: ['基础版（C系列）','专业版（D系列）','执法版（S系列）']},
  '云视讯': {L1: ['软终端','硬终端'], L2: {硬终端: ['桌面终端','智慧大屏','AI慧记本']}},
  '千里眼': {L1: ['有线千里眼','无线千里眼'], L2: {有线千里眼: ['7天云存储','30天云存储'], 无线千里眼: ['10G流量套餐','50G流量套餐','500G流量套餐']}}
};

let state = {
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  customerName: '',
  products: Array.from({length:5}, (_,i) => ({id:i, product:'', sub1:'', sub2:'', qty:'', detail:''})),
  voiceText: '',
  voiceResult: null,
  recording: false,
  recognition: null
};

const $ = id => document.getElementById(id);

// ============ REGISTER ============
if (!state.user) {
  showPage('register');
  const pos = $('reg-pos');
  pos.onchange = () => {
    $('reg-products-wrap').style.display = pos.value === '产品经理' ? '' : 'none';
    checkReg();
  };
  $('reg-name').oninput = checkReg;
  $('reg-dept').onchange = checkReg;
  renderProducts();
  $('btn-register').onclick = () => {
    const dept = $('reg-dept').value;
    const position = $('reg-pos').value;
    const products = [...$('reg-products').querySelectorAll('input:checked')].map(c => c.value);
    state.user = { name: $('reg-name').value, dept, position, products, productLine: '政企产品' };
    localStorage.setItem('user', JSON.stringify(state.user));
    showPage('main');
    initMain();
  };
} else {
  showPage('main');
  initMain();
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  $(`page-${name}`).style.display = '';
}

function renderProducts() {
  const wrap = $('reg-products');
  wrap.innerHTML = ALL_PRODUCTS.map(p => `<label><input type="checkbox" value="${p}"><span>${p}</span></label>`).join('');
  wrap.onchange = checkReg;
}

function checkReg() {
  const ok = $('reg-name').value && $('reg-dept').value && $('reg-pos').value;
  $('btn-register').disabled = !ok;
}

// ============ MAIN ============
function initMain() {
  $('greeting').textContent = `你好，${state.user.name}`;
  renderProductCards();
  initVoice();
}

function renderProductCards() {
  const html = state.products.map((p,i) => `
    <div class="card">
      <div class="card-title">需求产品${i+1}</div>
      <div class="field">
        <label>选择产品</label>
        <select data-idx="${i}" class="sel-product">${['请选择产品',...ALL_PRODUCTS].map(o => `<option ${p.product===o?'selected':''}>${o}</option>`).join('')}</select>
      </div>
      <div class="field sub1-wrap" style="display:${p.product&&SUB_OPTS[p.product]?'':'none'}">
        <label class="lbl-sub1"></label>
        <select data-idx="${i}" class="sel-sub1">${renderSub1(p)}</select>
      </div>
      <div class="field sub2-wrap" style="display:${hasL2(p)?'':'none'}">
        <label class="lbl-sub2"></label>
        <select data-idx="${i}" class="sel-sub2">${renderSub2(p)}</select>
      </div>
      <div class="field">
        <label>数量</label>
        <input class="half" data-idx="${i}" type="number" placeholder="数量" value="${p.qty}" oninput="upd(${i},'qty',this.value)">
      </div>
      <div class="field">
        <label>具体需求</label>
        <textarea data-idx="${i}" placeholder="请描述具体需求..." oninput="upd(${i},'detail',this.value)">${p.detail}</textarea>
      </div>
    </div>`).join('');
  $('product-cards').innerHTML = html;

  // Event listeners
  document.querySelectorAll('.sel-product').forEach(sel => {
    sel.onchange = function() {
      const i = +this.dataset.idx;
      state.products[i].product = this.value === '请选择产品' ? '' : this.value;
      state.products[i].sub1 = ''; state.products[i].sub2 = '';
      renderProductCards();
    };
  });
  document.querySelectorAll('.sel-sub1').forEach(sel => {
    sel.onchange = function() {
      const i = +this.dataset.idx;
      state.products[i].sub1 = this.value;
      state.products[i].sub2 = '';
      renderProductCards();
    };
  });
  document.querySelectorAll('.sel-sub2').forEach(sel => {
    sel.onchange = function() {
      state.products[i] = +this.dataset.idx;
      renderProductCards();
    };
  });
}

function renderSub1(p) {
  if (!p.product || !SUB_OPTS[p.product]) return '';
  const opts = SUB_OPTS[p.product];
  const lbl = $('.lbl-sub1') || {}; // ignore
  return ['请选择',...opts.L1].map(o => `<option ${p.sub1===o?'selected':''}>${o}</option>`).join('');
}
function renderSub2(p) {
  if (!p.product || !p.sub1) return '';
  const opts = SUB_OPTS[p.product];
  if (!opts.L2 || !opts.L2[p.sub1]) return '';
  return ['请选择',...opts.L2[p.sub1]].map(o => `<option ${p.sub2===o?'selected':''}>${o}</option>`).join('');
}
function hasL2(p) {
  if (!p.product || !p.sub1) return false;
  const opts = SUB_OPTS[p.product];
  return !!(opts && opts.L2 && opts.L2[p.sub1] && opts.L2[p.sub1].length > 0);
}
function upd(i, key, val) { state.products[i][key] = val; }

// ============ VOICE ============
function initVoice() {
  const btn = $('voice-btn');
  const ua = navigator.userAgent;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const isWeChat = /MicroMessenger/i.test(ua);
  const isIOS = /iPhone|iPad|iPod/i.test(ua);

  // 微信内置浏览器不支持
  if (isWeChat) {
    btn.textContent = '📱 微信内不支持语音';
    btn.disabled = true;
    btn.classList.add('disabled');
    $('voice-status').innerHTML = '请点击右上角 <b>「···」→「在浏览器中打开」</b>';
    $('voice-status').style.display = '';
    return;
  }

  // iOS 全系不支持
  if (!SpeechRecognition || isIOS) {
    btn.textContent = '⚠️ iOS 暂不支持语音';
    btn.disabled = true;
    $('voice-status').textContent = '请使用安卓手机或电脑端 Chrome';
    $('voice-status').style.display = '';
    return;
  }

  if (!SpeechRecognition) {
    btn.textContent = '⚠️ 浏览器不支持语音';
    btn.disabled = true;
    return;
  }

  let rec = null;

  function makeRec() {
    const r = new SpeechRecognition();
    r.lang = 'zh-CN';
    r.interimResults = false;
    r.continuous = false;

    r.onstart = () => {
      $('voice-status').textContent = '🎤 录音中...';
      $('voice-status').style.display = '';
    };

    r.onresult = (e) => {
      const text = e.results[0][0].transcript;
      state.voiceText = text;
      btn.classList.remove('recording');
      btn.textContent = '🎙️ 按住说话';
      state.recording = false;
      $('voice-result').style.display = '';
      $('voice-text-edit').value = text;
      $('voice-status').style.display = 'none';
    };

    r.onerror = (e) => {
      btn.classList.remove('recording');
      btn.textContent = '🎙️ 按住说话';
      state.recording = false;
      const msgs = {
        'not-allowed': '麦克风权限未授权，请在浏览器设置中允许',
        'no-speech': '未检测到语音，请靠近麦克风说话',
        'audio-capture': '未找到麦克风设备',
        'network': '网络连接失败'
      };
      $('voice-status').textContent = msgs[e.error] || ('识别失败: ' + e.error);
      $('voice-status').style.display = '';
    };

    r.onend = () => {
      btn.classList.remove('recording');
      btn.textContent = '🎙️ 按住说话';
      state.recording = false;
      if (!state.voiceResult) {
        $('voice-status').style.display = 'none';
      }
    };

    return r;
  }

  function startRecord(e) {
    e.preventDefault();
    btn.classList.add('recording');
    btn.textContent = '🔴 松开发送';
    state.recording = true;
    state.voiceText = '';
    $('voice-result').style.display = 'none';
    $('voice-ai-result').style.display = 'none';
    $('voice-status').textContent = '⏳ 请求麦克风...';
    $('voice-status').style.display = '';

    rec = makeRec();
    try {
      rec.start();
    } catch(err) {
      btn.classList.remove('recording');
      btn.textContent = '🎙️ 按住说话';
      state.recording = false;
      $('voice-status').textContent = '启动失败: ' + err.message;
    }
  }

  function stopRecord(e) {
    e.preventDefault();
    if (!state.recording || !rec) return;
    btn.classList.remove('recording');
    btn.textContent = '🎙️ 按住说话';
    state.recording = false;
    $('voice-status').textContent = '⏳ 识别中...';
    try { rec.stop(); } catch(err) {}
  }

  // 移动端优先 touch 事件
  btn.addEventListener('touchstart', startRecord, {passive: false});
  btn.addEventListener('touchend', stopRecord, {passive: false});
  btn.addEventListener('touchcancel', stopRecord, {passive: false});

  // 桌面端 mouse 事件兜底
  btn.addEventListener('mousedown', startRecord);
  btn.addEventListener('mouseup', stopRecord);
  btn.addEventListener('mouseleave', (e) => {
    if (state.recording && rec) {
      e.preventDefault();
      stopRecord(e);
    }
  });

  // 文字修改
  $('voice-text-edit').oninput = function() { state.voiceText = this.value; };

  // AI 分析
  $('btn-analyze').onclick = async () => {
    if (!state.voiceText) return;
    $('btn-analyze').textContent = '🤖 AI 分析中...';
    $('btn-analyze').disabled = true;

    try {
      const result = mockNlu(state.voiceText);
      state.voiceResult = result;
      renderAiResult(result);
    } catch(e) {
      $('voice-ai-result').innerHTML = '<div class="alert-err">分析失败: ' + e.message + '</div>';
    }
    $('btn-analyze').textContent = '🤖 AI 智能推荐产品';
    $('btn-analyze').disabled = false;
  };
}

function renderAiResult(result) {
  const wrap = $('voice-ai-result');
  wrap.style.display = '';
  const products = result.products.filter(p => p.product);
  wrap.innerHTML = `
    <div class="ai-result">
      <h3>🤖 AI 推荐</h3>
      ${result.customerName ? `<div class="ai-customer"><span>客户：</span><strong>${result.customerName}</strong></div>` : ''}
      <div class="ai-summary">${result.summary}</div>
      ${products.length > 0 ? products.map(p => `
        <div class="ai-item"><span class="name">${p.product}${p.subModel1?' · '+p.subModel1:''}${p.subModel2?' · '+p.subModel2:''}</span><span class="qty">×${p.quantity||1}</span></div>
      `).join('') : '<p style="font-size:14px;color:#999">未识别到具体产品，请手动选择</p>'}
      <button class="btn btn-green" onclick="fillForm()" style="margin-top:12px">📋 一键填入表单</button>
    </div>`;
}

function fillForm() {
  if (!state.voiceResult) return;
  const r = state.voiceResult;
  if (r.customerName) state.customerName = r.customerName;
  $('customer-name').value = r.customerName || '';

  let slot = 0;
  r.products.forEach(rp => {
    if (!rp.product || slot >= 5) return;
    state.products[slot].product = rp.product;
    state.products[slot].sub1 = rp.subModel1 || '';
    state.products[slot].sub2 = rp.subModel2 || '';
    state.products[slot].qty = String(rp.quantity || 1);
    state.products[slot].detail = rp.detail || '';
    slot++;
  });
  renderProductCards();
  alert('已填入表单！');
}

// ============ NLU (Mock) ============
function mockNlu(text) {
  const lower = text.toLowerCase();
  const hints = [
    {k:['对讲','对讲机','外勤','执法','跑外','调度'], p:'和对讲', s1: lower.includes('专业')||lower.includes('d系列')?'专业版（D系列）':lower.includes('执法')||lower.includes('s系列')?'执法版（S系列）':'基础版（C系列）'},
    {k:['监控','摄像头','千里眼','安防','防盗','仓库','探头'], p:'千里眼', s1: lower.includes('无线')?'无线千里眼':'有线千里眼', s2: lower.includes('30')?'30天云存储':lower.includes('500')?'500G流量套餐':lower.includes('50')?'50G流量套餐':'7天云存储'},
    {k:['会议','视频','开会','云视讯','投屏','大屏'], p:'云视讯', s1: lower.includes('硬')||lower.includes('大屏')?'硬终端':'软终端', s2: lower.includes('大屏')?'智慧大屏':lower.includes('慧记')?'AI慧记本':lower.includes('桌面')?'桌面终端':''},
    {k:['专线','宽带','光纤','上网'], p:'专线'},
    {k:['短信','彩信','群发','营销'], p:'短彩信'},
    {k:['车队','车辆','gps','定位'], p:'和车队'},
    {k:['云','服务器','存储','云计算'], p:'移动云'},
    {k:['物联','iot','sim卡','传感器'], p:'物联网'}
  ];
  const matched = [];
  hints.forEach(h => {
    if (h.k.some(kw => lower.includes(kw))) matched.push({product:h.p, subModel1:h.s1||'', subModel2:h.s2||'', quantity: (text.match(/\d+/)?.[0]||1), detail:''});
  });
  const nm = text.match(/([\u4e00-\u9fa5]{2,10}(?:公司|集团|企业|厂|店|行|局|中心|学校|医院|政府|单位|营业厅))/)?.[1] || '';
  return { customerName: nm, customerType:'', budget:null, headcount:null, products: matched.length ? matched : [{product:'',subModel1:'',subModel2:'',quantity:1,detail:text.slice(0,50)}], summary:text };
}

// ============ SUBMIT ============
$('customer-name').oninput = function() { state.customerName = this.value; };

$('btn-submit').onclick = () => {
  const filled = state.products.filter(p => p.product);
  if (!state.customerName) return alert('请输入客户名称');
  if (!filled.length) return alert('请至少选择一个产品');

  const order = {
    customerName: state.customerName,
    products: filled.map(p => ({
      product: p.product,
      sub: [p.sub1, p.sub2].filter(Boolean).join(' · '),
      qty: parseInt(p.qty) || 1,
      detail: p.detail
    })),
    createdBy: state.user.name,
    time: new Date().toLocaleString()
  };

  const html = `
    <div class="order-box">
      <h3>📋 需求清单</h3>
      <div class="order-row"><span class="label">客户：</span>${order.customerName}</div>
      <div class="order-row"><span class="label">提交人：</span>${order.createdBy}</div>
      <div class="order-row"><span class="label">时间：</span>${order.time}</div>
      <table class="order-table">
        <tr><th>序号</th><th>产品名称</th><th>数量</th><th>具体需求</th></tr>
        ${order.products.map((p,i) => `<tr><td>${i+1}</td><td>${p.product}${p.sub?'（'+p.sub+'）':''}</td><td>${p.qty}</td><td>${p.detail||'—'}</td></tr>`).join('')}
      </table>
    </div>`;
  $('order-result').innerHTML = html;
  $('order-result').style.display = '';
};
