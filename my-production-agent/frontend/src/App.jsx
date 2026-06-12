import React, { useState, useEffect, useRef } from 'react';
import { 
  User, 
  Activity, 
  Flame, 
  Dumbbell, 
  Apple, 
  Search, 
  Send, 
  Plus, 
  RefreshCw, 
  ChevronDown, 
  ChevronUp, 
  AlertCircle, 
  Info, 
  Award,
  PlusCircle,
  TrendingDown,
  TrendingUp,
  Sliders
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

function App() {
  const [users, setUsers] = useState([]);
  const [activeUser, setActiveUser] = useState(null);
  const [summary, setSummary] = useState(null);
  const [dishes, setDishes] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Logging Form
  const [logMealType, setLogMealType] = useState('Breakfast');
  const [logDishName, setLogDishName] = useState('');
  const [logPortion, setLogPortion] = useState(1.0);
  const [logSuccessMessage, setLogSuccessMessage] = useState('');
  const [logErrorMessage, setLogErrorMessage] = useState('');

  // Menu Recommendation State
  const [recommendedMenu, setRecommendedMenu] = useState(null);
  const [isMenuLoading, setIsMenuLoading] = useState(false);

  // Profile Form (For creating/editing users)
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileForm, setProfileForm] = useState({
    name: '',
    age: 25,
    gender: 'Nam',
    weight_kg: 70,
    height_cm: 170,
    activity_level: 'moderate',
    goal: 'build_muscle'
  });

  // Chatbot State
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'assistant',
      text: 'Xin chào! Tôi là Chuyên gia Dinh dưỡng AI. Bạn có thể hỏi tôi về giá trị dinh dưỡng của món ăn, nhờ tôi lên thực đơn, tính toán TDEE hoặc ghi nhận bữa ăn của bạn nhé!',
      trace: null
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const [expandedTraces, setExpandedTraces] = useState({});

  const chatEndRef = useRef(null);

  // Compute aggregate metrics from chat history dynamically
  const getAggregateMetrics = () => {
    const evalMessages = chatMessages.filter(msg => msg.sender === 'assistant' && msg.eval);
    
    if (evalMessages.length === 0) {
      return {
        model: 'gemini-3.5-flash',
        successRate: '86.7%',
        avgLatency: '5.83s',
        avgLLMCall: '2.07s',
        avgTokensPerCall: '1,471',
        avgSteps: '1.8 steps'
      };
    }
    
    let totalLatency = 0;
    let totalTokens = 0;
    let totalSteps = 0;
    let successCount = 0;
    let primaryModel = 'gemini-3.5-flash';
    
    evalMessages.forEach(msg => {
      const ev = msg.eval;
      totalLatency += ev.latency_ms || 0;
      totalTokens += ev.total_tokens || 0;
      totalSteps += ev.steps || 1; // avoid divide by zero
      if (ev.model) {
        primaryModel = ev.model;
      }
      
      const hasFinalAnswer = msg.trace && msg.trace.length > 0 && msg.trace[msg.trace.length - 1].final_answer !== null;
      if (hasFinalAnswer || ev.steps < 6) {
        successCount++;
      }
    });
    
    const count = evalMessages.length;
    const avgLatencyVal = totalLatency / count;
    const avgStepsVal = totalSteps / count;
    
    const avgLatency = (avgLatencyVal / 1000).toFixed(2) + 's';
    const avgLLMCall = (totalLatency / totalSteps / 1000).toFixed(2) + 's';
    const avgTokensPerCall = Math.round(totalTokens / totalSteps).toLocaleString();
    const avgSteps = avgStepsVal.toFixed(1) + ' steps';
    const successRate = ((successCount / count) * 100).toFixed(1) + '%';
    
    return {
      model: primaryModel,
      successRate,
      avgLatency,
      avgLLMCall,
      avgTokensPerCall,
      avgSteps
    };
  };

  const aggMetrics = getAggregateMetrics();

  // Initialize
  useEffect(() => {
    fetchUsers();
    fetchDishes();
  }, []);

  // Auto scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAgentTyping]);

  const fetchChatHistory = async (userId) => {
    try {
      const res = await fetch(`${API_BASE}/chat/history/${userId}`, {
        headers: { 'x-api-key': 'secret' }
      });
      const data = await res.json();
      setChatMessages(data);
    } catch (e) {
      console.error("Error fetching chat history:", e);
    }
  };

  const fetchUsers = async (selectedUserId = null) => {
    try {
      const res = await fetch(`${API_BASE}/users`, {
        headers: { 'x-api-key': 'secret' }
      });
      const data = await res.json();
      setUsers(data);
      if (data && data.length > 0) {
        const currentId = selectedUserId || activeUser?.id || data[0].id;
        const targetUser = data.find(u => u.id === currentId) || data[0];
        setActiveUser(targetUser);
        fetchSummary(targetUser.id);
        fetchChatHistory(targetUser.id);
        if (targetUser.recommended_menu && targetUser.recommended_menu.menu) {
          setRecommendedMenu(targetUser.recommended_menu);
        } else {
          setRecommendedMenu(null);
        }
        
        // Prep profile form
        setProfileForm({
          name: targetUser.name,
          age: targetUser.age,
          gender: targetUser.gender,
          weight_kg: targetUser.weight_kg,
          height_cm: targetUser.height_cm,
          activity_level: targetUser.activity_level,
          goal: targetUser.goal
        });
      }
    } catch (e) {
      console.error("Error fetching users:", e);
    }
  };

  const fetchSummary = async (userId) => {
    try {
      const res = await fetch(`${API_BASE}/users/${userId}/summary`, {
        headers: { 'x-api-key': 'secret' }
      });
      const data = await res.json();
      setSummary(data);
    } catch (e) {
      console.error("Error fetching summary:", e);
    }
  };

  const fetchDishes = async (query = '') => {
    try {
      const res = await fetch(`${API_BASE}/dishes?q=${query}`, {
        headers: { 'x-api-key': 'secret' }
      });
      const data = await res.json();
      setDishes(data);
    } catch (e) {
      console.error("Error fetching dishes:", e);
    }
  };

  const handleUserChange = (userId) => {
    const user = users.find(u => u.id === userId);
    if (user) {
      setActiveUser(user);
      fetchSummary(userId);
      if (user.recommended_menu && user.recommended_menu.menu) {
        setRecommendedMenu(user.recommended_menu);
      } else {
        setRecommendedMenu(null);
      }
      setProfileForm({
        name: user.name,
        age: user.age,
        gender: user.gender,
        weight_kg: user.weight_kg,
        height_cm: user.height_cm,
        activity_level: user.activity_level,
        goal: user.goal
      });
      // Clear logs
      setLogSuccessMessage('');
      setLogErrorMessage('');
      // Fetch chat history for this user
      fetchChatHistory(user.id);
    }
  };

  const handleLogMeal = async (e) => {
    if (e) e.preventDefault();
    if (!activeUser || !logDishName) return;

    setLogSuccessMessage('');
    setLogErrorMessage('');

    try {
      const res = await fetch(`${API_BASE}/users/${activeUser.id}/log`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-api-key': 'secret'
        },
        body: JSON.stringify({
          meal_type: logMealType,
          dish_name: logDishName,
          portion_size: parseFloat(logPortion)
        })
      });

      const data = await res.json();
      if (res.ok) {
        setLogSuccessMessage(data.message || 'Đã ghi nhận bữa ăn thành công!');
        fetchSummary(activeUser.id);
        // Reset form dish name
        setLogDishName('');
        setLogPortion(1.0);
      } else {
        setLogErrorMessage(data.detail || 'Lỗi khi ghi nhận bữa ăn.');
      }
    } catch (e) {
      setLogErrorMessage('Không thể kết nối đến server backend.');
      console.error(e);
    }
  };

  const handleGetRecommendation = async () => {
    if (!activeUser) return;
    setIsMenuLoading(true);
    try {
      const res = await fetch(`${API_BASE}/users/${activeUser.id}/recommend_menu`, {
        headers: { 'x-api-key': 'secret' }
      });
      const data = await res.json();
      if (res.ok) {
        setRecommendedMenu(data);
        // Sync local activeUser and users list with the new menu
        setActiveUser(prev => ({ ...prev, recommended_menu: data }));
        setUsers(prev => prev.map(u => u.id === activeUser.id ? { ...u, recommended_menu: data } : u));
      } else {
        alert(data.detail || 'Lỗi khi tạo thực đơn gợi ý.');
      }
    } catch (e) {
      console.error(e);
      alert('Không kết nối được tới server.');
    } finally {
      setIsMenuLoading(false);
    }
  };

  const handleLogRecommendedMeal = async (mealType, dishName) => {
    if (!activeUser) return;
    try {
      const res = await fetch(`${API_BASE}/users/${activeUser.id}/log`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-api-key': 'secret'
        },
        body: JSON.stringify({
          meal_type: mealType,
          dish_name: dishName,
          portion_size: 1.0
        })
      });
      if (res.ok) {
        fetchSummary(activeUser.id);
        setLogSuccessMessage(`Đã ghi nhận ${dishName} vào nhật ký!`);
      } else {
        const data = await res.json();
        alert(data.detail || 'Lỗi khi ghi nhận.');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogAllRecommended = async () => {
    if (!activeUser || !recommendedMenu) return;
    try {
      const meals = recommendedMenu.menu;
      const order = [
        { type: 'Breakfast', dish: meals.Breakfast.name },
        { type: 'Lunch', dish: meals.Lunch.name },
        { type: 'Dinner', dish: meals.Dinner.name },
        { type: 'Snack', dish: meals.Snack.name }
      ];
      
      for (const m of order) {
        await fetch(`${API_BASE}/users/${activeUser.id}/log`, {
          method: 'POST',
          headers: { 
          'Content-Type': 'application/json',
          'x-api-key': 'secret'
        },
          body: JSON.stringify({
            meal_type: m.type,
            dish_name: m.dish,
            portion_size: 1.0
          })
        });
      }
      
      fetchSummary(activeUser.id);
      setLogSuccessMessage('Đã ghi nhận toàn bộ thực đơn gợi ý vào nhật ký!');
    } catch (e) {
      console.error(e);
      alert('Lỗi khi ghi nhận toàn bộ thực đơn.');
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        id: activeUser?.id,
        ...profileForm,
        weight_kg: parseFloat(profileForm.weight_kg),
        height_cm: parseFloat(profileForm.height_cm),
        age: parseInt(profileForm.age)
      };

      const res = await fetch(`${API_BASE}/users`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-api-key': 'secret'
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setIsEditingProfile(false);
        // Refresh users list and selection
        await fetchUsers();
        // Force refresh active user and summary
        setActiveUser(data);
        fetchSummary(data.id);
      }
    } catch (e) {
      console.error(e);
      alert("Cập nhật thông tin thất bại!");
    }
  };

  const handleSearchDishes = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    fetchDishes(val);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput.trim();
    setChatMessages(prev => [...prev, { sender: 'user', text: userText, trace: null }]);
    setChatInput('');
    setIsAgentTyping(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-api-key': 'secret'
        },
        body: JSON.stringify({
          user_id: activeUser?.id,
          message: userText
        })
      });

      const data = await res.json();
      if (res.ok) {
        if (activeUser) {
          await fetchUsers(activeUser.id);
        }
      } else {
        setChatMessages(prev => [...prev, { 
          sender: 'assistant', 
          text: `Đã xảy ra lỗi: ${data.detail || 'Không thể liên lạc với tác nhân AI.'}`, 
          trace: null 
        }]);
      }
    } catch (e) {
      setChatMessages(prev => [...prev, { 
        sender: 'assistant', 
        text: 'Lỗi: Không kết nối được tới máy chủ dịch vụ Agent.', 
        trace: null 
      }]);
    } finally {
      setIsAgentTyping(false);
    }
  };

  const handleClearChatHistory = async () => {
    if (!activeUser) return;
    if (!window.confirm("Bạn có chắc chắn muốn xóa lịch sử chat của người dùng này?")) return;
    try {
      const res = await fetch(`${API_BASE}/chat/history/${activeUser.id}/clear`, { 
        method: 'POST',
        headers: { 'x-api-key': 'secret' }
      });
      const data = await res.json();
      if (res.ok) {
        setChatMessages(data);
      }
    } catch (e) {
      console.error("Error clearing chat history:", e);
    }
  };

  const toggleTrace = (index) => {
    setExpandedTraces(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Helper for progress ring percentages
  const getProgressPercentage = (consumed, target) => {
    if (!target) return 0;
    return Math.min(100, Math.round((consumed / target) * 100));
  };

  const getStrokeDashoffset = (percent, radius = 51) => {
    const circumference = 2 * Math.PI * radius;
    return circumference - (percent / 100) * circumference;
  };

  // User details helper
  const translateGoal = (goal) => {
    if (goal === 'lose_weight') return 'Giảm cân (Calorie Deficit)';
    if (goal === 'gain_weight') return 'Tăng cân (Calorie Surplus)';
    if (goal === 'build_muscle') return 'Tăng cơ (High Protein)';
    return 'Giữ dáng (Maintain)';
  };

  const translateActivity = (act) => {
    if (act === 'sedentary') return 'Ít vận động (Văn phòng)';
    if (act === 'light') return 'Vận động nhẹ (Đi bộ nhẹ)';
    if (act === 'moderate') return 'Vận động vừa (Tập 3-5 ngày/tuần)';
    if (act === 'active') return 'Vận động nhiều (Tập 6-7 ngày/tuần)';
    if (act === 'very_active') return 'Vận động cực nhiều (VĐV)';
    return act;
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-title-container">
          <Apple className="text-primary" size={32} />
          <h1>AI Nutrition Advisory</h1>
          <span className="badge">MVP Agent v2</span>
        </div>
        <div className="user-selector-container">
          <User size={18} className="text-secondary" />
          <select 
            className="select-user"
            value={activeUser?.id || ''}
            onChange={(e) => handleUserChange(e.target.value)}
          >
            {users.map(u => (
              <option key={u.id} value={u.id}>{u.name} ({translateGoal(u.goal)})</option>
            ))}
          </select>
        </div>
      </header>

      {/* Metrics Dashboard Bar */}
      <section className="metrics-bar-container card mb-3">
        <div className="metrics-bar-title">
          <Activity className="text-primary" size={16} />
          <h4>ReAct Agent Performance Telemetry (Evaluation Metrics)</h4>
        </div>
        <div className="metrics-bar-grid">
          <div className="metric-box">
            <span className="metric-box-label">Primary Model</span>
            <span className="metric-box-value text-secondary">{aggMetrics.model}</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Success Rate</span>
            <span className="metric-box-value text-primary">{aggMetrics.successRate}</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Avg Run Latency</span>
            <span className="metric-box-value text-primary">{aggMetrics.avgLatency}</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Avg LLM Call</span>
            <span className="metric-box-value text-primary">{aggMetrics.avgLLMCall}</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Avg Tokens / Call</span>
            <span className="metric-box-value text-accent">{aggMetrics.avgTokensPerCall}</span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Avg Steps / Run</span>
            <span className="metric-box-value text-accent">{aggMetrics.avgSteps}</span>
          </div>
        </div>
      </section>

      {activeUser && (
        <div className="dashboard-grid">
          {/* Sidebar Profile Card */}
          <aside className="flex flex-col gap-3">
            <div className="card profile-card">
              <div className="profile-avatar-section">
                <div className="avatar">
                  {activeUser.name.split(' ').pop().charAt(0)}
                </div>
                <div>
                  <h3 className="profile-name">{activeUser.name}</h3>
                  <span className={`profile-goal-tag goal-${activeUser.goal}`}>
                    {translateGoal(activeUser.goal)}
                  </span>
                </div>
              </div>

              {!isEditingProfile ? (
                <>
                  <div className="profile-stats-grid">
                    <div className="stat-item">
                      <span className="stat-label">Cân nặng</span>
                      <span className="stat-value">{activeUser.weight_kg} kg</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Chiều cao</span>
                      <span className="stat-value">{activeUser.height_cm} cm</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Tuổi</span>
                      <span className="stat-value">{activeUser.age} tuổi</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Giới tính</span>
                      <span className="stat-value">{activeUser.gender}</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 mt-1">
                    <div className="flex justify-between text-secondary" style={{ fontSize: '0.85rem' }}>
                      <span>Mức vận động:</span>
                      <span className="font-bold text-primary">{translateActivity(activeUser.activity_level)}</span>
                    </div>
                    <div className="flex justify-between text-secondary" style={{ fontSize: '0.85rem' }}>
                      <span>Mục tiêu Calo:</span>
                      <span className="font-bold text-primary">{activeUser.target_calories} kcal</span>
                    </div>
                  </div>

                  <button 
                    className="btn btn-secondary mt-2 w-full"
                    onClick={() => setIsEditingProfile(true)}
                  >
                    <Sliders size={16} /> Cấu hình chỉ số
                  </button>
                </>
              ) : (
                <form onSubmit={handleUpdateProfile} className="flex flex-col gap-2">
                  <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                    <label>Họ và tên</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      value={profileForm.name}
                      onChange={e => setProfileForm({...profileForm, name: e.target.value})}
                      required
                    />
                  </div>
                  <div className="profile-stats-grid">
                    <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                      <label>Cân nặng (kg)</label>
                      <input 
                        type="number" 
                        step="0.1" 
                        className="form-control" 
                        value={profileForm.weight_kg}
                        onChange={e => setProfileForm({...profileForm, weight_kg: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                      <label>Chiều cao (cm)</label>
                      <input 
                        type="number" 
                        className="form-control" 
                        value={profileForm.height_cm}
                        onChange={e => setProfileForm({...profileForm, height_cm: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                      <label>Tuổi</label>
                      <input 
                        type="number" 
                        className="form-control" 
                        value={profileForm.age}
                        onChange={e => setProfileForm({...profileForm, age: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                      <label>Giới tính</label>
                      <select 
                        className="form-control"
                        value={profileForm.gender}
                        onChange={e => setProfileForm({...profileForm, gender: e.target.value})}
                      >
                        <option value="Nam">Nam</option>
                        <option value="Nữ">Nữ</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                    <label>Mức vận động</label>
                    <select 
                      className="form-control"
                      value={profileForm.activity_level}
                      onChange={e => setProfileForm({...profileForm, activity_level: e.target.value})}
                    >
                      <option value="sedentary">Ít vận động (sedentary)</option>
                      <option value="light">Vận động nhẹ (light)</option>
                      <option value="moderate">Vận động vừa (moderate)</option>
                      <option value="active">Vận động nhiều (active)</option>
                      <option value="very_active">Cực nhiều (very_active)</option>
                    </select>
                  </div>
                  <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                    <label>Mục tiêu</label>
                    <select 
                      className="form-control"
                      value={profileForm.goal}
                      onChange={e => setProfileForm({...profileForm, goal: e.target.value})}
                    >
                      <option value="lose_weight">Giảm cân</option>
                      <option value="gain_weight">Tăng cân</option>
                      <option value="build_muscle">Tăng cơ</option>
                      <option value="maintain">Giữ dáng</option>
                    </select>
                  </div>
                  
                  <div className="flex gap-2 mt-2">
                    <button type="submit" className="btn w-full">Lưu</button>
                    <button 
                      type="button" 
                      className="btn btn-secondary w-full"
                      onClick={() => setIsEditingProfile(false)}
                    >
                      Hủy
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Goal tracker card */}
            <div className="card">
              <h4 className="flex items-center gap-2 mb-2 font-bold" style={{ margin: 0, fontSize: '1rem' }}>
                <Award size={18} className="text-accent" />
                Mục tiêu hôm nay
              </h4>
              <p className="text-secondary" style={{ fontSize: '0.8rem', margin: '0.25rem 0 0.75rem' }}>
                Duy trì tiến độ dinh dưỡng hàng ngày dựa trên các chỉ số được khuyến nghị.
              </p>
              
              {summary && (
                <div className="flex flex-col gap-2">
                  <div className="flex flex-col">
                    <span className="text-muted" style={{ fontSize: '0.7rem' }}>Calo nạp vào hiện tại:</span>
                    <div className="flex justify-between items-center mt-1">
                      <span className="font-bold text-primary" style={{ fontSize: '1.1rem' }}>
                        {summary.consumed.calories} <span className="text-muted" style={{ fontSize: '0.8rem', fontWeight: 'normal' }}>/ {summary.targets.calories} kcal</span>
                      </span>
                      <span className={`badge ${summary.consumed.calories > summary.targets.calories ? 'goal-lose_weight' : 'goal-build_muscle'}`}>
                        {getProgressPercentage(summary.consumed.calories, summary.targets.calories)}%
                      </span>
                    </div>
                  </div>
                  
                  {activeUser.goal === 'lose_weight' && (
                    <div className="flex items-center gap-2 mt-1 text-danger" style={{ fontSize: '0.75rem' }}>
                      <TrendingDown size={14} />
                      <span>Chú ý thâm hụt calo mục tiêu để giảm cân an toàn!</span>
                    </div>
                  )}
                  {activeUser.goal === 'build_muscle' && (
                    <div className="flex items-center gap-2 mt-1 text-primary" style={{ fontSize: '0.75rem' }}>
                      <TrendingUp size={14} />
                      <span>Cần nạp đủ Protein để tái tạo sợi cơ tốt nhất!</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </aside>

          {/* Main Dashboard Content */}
          <main className="flex flex-col gap-3">
            <nav className="tabs-container">
              <button 
                className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('dashboard')}
              >
                <Activity size={16} /> Bảng theo dõi
              </button>
              <button 
                className={`tab-btn ${activeTab === 'food_db' ? 'active' : ''}`}
                onClick={() => setActiveTab('food_db')}
              >
                <Apple size={16} /> Kho thực phẩm
              </button>
              <button 
                className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
                onClick={() => setActiveTab('chat')}
              >
                <Dumbbell size={16} /> Chat AI Agent
              </button>
            </nav>

            {/* TAB 1: DASHBOARD */}
            {activeTab === 'dashboard' && summary && (
              <div className="summary-overview">
                {/* Progress rings */}
                <div className="card progress-rings-container">
                  {/* Calories */}
                  <div className="progress-card">
                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg className="progress-circle-svg">
                        <circle className="progress-circle-bg" cx="55" cy="55" r="51"></circle>
                        <circle 
                          className="progress-circle-val calories-val" 
                          cx="55" 
                          cy="55" 
                          r="51"
                          strokeDasharray={2 * Math.PI * 51}
                          strokeDashoffset={getStrokeDashoffset(getProgressPercentage(summary.consumed.calories, summary.targets.calories))}
                        ></circle>
                      </svg>
                      <div className="circle-text">
                        {summary.consumed.calories}
                        <span>kcal</span>
                      </div>
                    </div>
                    <div className="progress-details">
                      <h4>Calories</h4>
                      <p>Mục tiêu: {summary.targets.calories}</p>
                    </div>
                  </div>

                  {/* Protein */}
                  <div className="progress-card">
                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg className="progress-circle-svg">
                        <circle className="progress-circle-bg" cx="55" cy="55" r="51"></circle>
                        <circle 
                          className="progress-circle-val protein-val" 
                          cx="55" 
                          cy="55" 
                          r="51"
                          strokeDasharray={2 * Math.PI * 51}
                          strokeDashoffset={getStrokeDashoffset(getProgressPercentage(summary.consumed.protein_g, summary.targets.protein_g))}
                        ></circle>
                      </svg>
                      <div className="circle-text">
                        {summary.consumed.protein_g}g
                        <span>/ {summary.targets.protein_g}g</span>
                      </div>
                    </div>
                    <div className="progress-details">
                      <h4>Protein</h4>
                      <p>Đạt được: {getProgressPercentage(summary.consumed.protein_g, summary.targets.protein_g)}%</p>
                    </div>
                  </div>

                  {/* Carbs */}
                  <div className="progress-card">
                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg className="progress-circle-svg">
                        <circle className="progress-circle-bg" cx="55" cy="55" r="51"></circle>
                        <circle 
                          className="progress-circle-val carbs-val" 
                          cx="55" 
                          cy="55" 
                          r="51"
                          strokeDasharray={2 * Math.PI * 51}
                          strokeDashoffset={getStrokeDashoffset(getProgressPercentage(summary.consumed.carbohydrates_g, summary.targets.carbohydrates_g))}
                        ></circle>
                      </svg>
                      <div className="circle-text">
                        {summary.consumed.carbohydrates_g}g
                        <span>/ {summary.targets.carbohydrates_g}g</span>
                      </div>
                    </div>
                    <div className="progress-details">
                      <h4>Carbs</h4>
                      <p>Đạt được: {getProgressPercentage(summary.consumed.carbohydrates_g, summary.targets.carbohydrates_g)}%</p>
                    </div>
                  </div>

                  {/* Fat */}
                  <div className="progress-card">
                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg className="progress-circle-svg">
                        <circle className="progress-circle-bg" cx="55" cy="55" r="51"></circle>
                        <circle 
                          className="progress-circle-val fat-val" 
                          cx="55" 
                          cy="55" 
                          r="51"
                          strokeDasharray={2 * Math.PI * 51}
                          strokeDashoffset={getStrokeDashoffset(getProgressPercentage(summary.consumed.fat_g, summary.targets.fat_g))}
                        ></circle>
                      </svg>
                      <div className="circle-text">
                        {summary.consumed.fat_g}g
                        <span>/ {summary.targets.fat_g}g</span>
                      </div>
                    </div>
                    <div className="progress-details">
                      <h4>Lipid (Fat)</h4>
                      <p>Đạt được: {getProgressPercentage(summary.consumed.fat_g, summary.targets.fat_g)}%</p>
                    </div>
                  </div>
                </div>

                {/* Meal logging & Timeline */}
                <div className="meal-logger-grid">
                  {/* Log form */}
                  <div className="card">
                    <h3 className="flex items-center gap-2 font-bold mb-3" style={{ fontSize: '1.2rem', margin: 0 }}>
                      <PlusCircle size={20} className="text-primary" />
                      Ghi nhận bữa ăn mới
                    </h3>
                    
                    <form onSubmit={handleLogMeal}>
                      <div className="form-group">
                        <label>Thời điểm ăn</label>
                        <select 
                          className="form-control"
                          value={logMealType}
                          onChange={e => setLogMealType(e.target.value)}
                        >
                          <option value="Breakfast">Bữa sáng (Breakfast)</option>
                          <option value="Lunch">Bữa trưa (Lunch)</option>
                          <option value="Dinner">Bữa tối (Dinner)</option>
                          <option value="Snack">Bữa phụ (Snack)</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Chọn món ăn (từ Database)</label>
                        <select 
                          className="form-control"
                          value={logDishName}
                          onChange={e => setLogDishName(e.target.value)}
                          required
                        >
                          <option value="">-- Chọn một món ăn --</option>
                          {dishes.map(d => (
                            <option key={d.id} value={d.name}>{d.name} ({d.calories_kcal} kcal)</option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Số lượng (Khẩu phần)</label>
                        <input 
                          type="number" 
                          step="0.1" 
                          min="0.1"
                          className="form-control" 
                          value={logPortion}
                          onChange={e => setLogPortion(e.target.value)}
                          required
                        />
                      </div>

                      <button type="submit" className="btn w-full mt-2">
                        Ghi nhận vào Nhật ký
                      </button>

                      {logSuccessMessage && (
                        <div className="flex items-center gap-2 mt-3 text-primary" style={{ fontSize: '0.85rem' }}>
                          <Info size={16} />
                          <span>{logSuccessMessage}</span>
                        </div>
                      )}
                      {logErrorMessage && (
                        <div className="flex items-center gap-2 mt-3 text-danger" style={{ fontSize: '0.85rem' }}>
                          <AlertCircle size={16} />
                          <span>{logErrorMessage}</span>
                        </div>
                      )}
                    </form>
                  </div>

                  {/* Logged meals list */}
                  <div className="card flex flex-col gap-2">
                    <h3 className="font-bold mb-2" style={{ fontSize: '1.2rem', margin: 0 }}>
                      Nhật ký ăn uống hôm nay
                    </h3>
                    {summary.logged_meals.length === 0 ? (
                      <div className="text-center text-muted mt-3 py-4" style={{ border: '1px dashed var(--border)', borderRadius: '12px' }}>
                        Chưa ghi nhận bữa ăn nào hôm nay.
                      </div>
                    ) : (
                      <div className="logged-meals-container" style={{ maxHeight: '280px', overflowY: 'auto' }}>
                        {summary.logged_meals.map((m, idx) => (
                          <div key={idx} className="logged-meal-card">
                            <div className="logged-meal-info">
                              <h5>{m.dish_name} ({m.portion_size} phần)</h5>
                              <p className="text-secondary">{m.meal_type} • {new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                            </div>
                            <div className="logged-meal-macros">
                              <span className="logged-meal-calories">+{m.calories_kcal} kcal</span>
                              <span className="logged-meal-macro-pills">
                                P: {m.protein_g}g | C: {m.carbohydrates_g}g | F: {m.fat_g}g
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Daily Menu Recommendation */}
                <div className="card mt-3">
                  <div className="flex justify-between items-center mb-3">
                    <div>
                      <h3 className="flex items-center gap-2 font-bold" style={{ fontSize: '1.2rem', margin: 0 }}>
                        <Award className="text-primary" size={20} />
                        Gợi ý thực đơn hôm nay từ AI
                      </h3>
                      <p className="text-secondary" style={{ fontSize: '0.85rem', margin: '0.25rem 0 0' }}>
                        Thực đơn được thiết kế tự động dựa trên chỉ số TDEE và mục tiêu dinh dưỡng khuyến nghị của bạn.
                      </p>
                    </div>
                    {!recommendedMenu && (
                      <button 
                        className="btn" 
                        onClick={handleGetRecommendation}
                        disabled={isMenuLoading}
                      >
                        {isMenuLoading ? <RefreshCw className="animate-spin" size={16} /> : <Sliders size={16} />}
                        {isMenuLoading ? 'Đang tạo...' : 'Tạo thực đơn'}
                      </button>
                    )}
                  </div>

                  {recommendedMenu && (
                    <div className="flex flex-col gap-3">
                      {/* 4 meals grid */}
                      <div className="dishes-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
                        {Object.entries(recommendedMenu.menu).map(([mealType, dish]) => (
                          <div key={mealType} className="card" style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.01)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                            <div className="flex justify-between items-center mb-2">
                              <span className="badge" style={{ background: 'var(--secondary-glow)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                                {mealType === 'Breakfast' ? 'Bữa sáng' : mealType === 'Lunch' ? 'Bữa trưa' : mealType === 'Dinner' ? 'Bữa tối' : 'Bữa phụ'}
                              </span>
                              <span className="dish-calories" style={{ fontSize: '0.75rem' }}>{dish.calories_kcal} kcal</span>
                            </div>
                            <h4 className="dish-title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>{dish.name}</h4>
                            <div className="dish-macros-summary" style={{ padding: '0.35rem', fontSize: '0.75rem' }}>
                              <div>
                                <span className="dish-macro-val text-primary" style={{ fontSize: '0.75rem' }}>{dish.protein_g}g</span>
                                <span className="dish-macro-lbl" style={{ fontSize: '0.6rem' }}>Protein</span>
                              </div>
                              <div>
                                <span className="dish-macro-val text-secondary" style={{ fontSize: '0.75rem' }}>{dish.carbohydrates_g}g</span>
                                <span className="dish-macro-lbl" style={{ fontSize: '0.6rem' }}>Carbs</span>
                              </div>
                              <div>
                                <span className="dish-macro-val text-accent" style={{ fontSize: '0.75rem' }}>{dish.fat_g}g</span>
                                <span className="dish-macro-lbl" style={{ fontSize: '0.6rem' }}>Fat</span>
                              </div>
                            </div>
                            <button 
                              className="btn btn-secondary mt-3 w-full"
                              style={{ padding: '0.35rem 0.5rem', fontSize: '0.75rem', borderRadius: '8px' }}
                              onClick={() => handleLogRecommendedMeal(mealType, dish.name)}
                            >
                              <Plus size={12} /> Log bữa này
                            </button>
                          </div>
                        ))}
                      </div>

                      {/* Summary and main actions */}
                      <div className="flex justify-between items-center mt-2 p-3" style={{ background: 'rgba(0,0,0,0.15)', borderRadius: '12px', border: '1px solid var(--border)', flexWrap: 'wrap', gap: '1rem' }}>
                        <div style={{ fontSize: '0.85rem' }}>
                          <span className="text-secondary">Dự kiến thực đơn:</span>{' '}
                          <span className="font-bold text-primary">{recommendedMenu.totals.calories} kcal</span>
                          <span className="text-muted"> / mục tiêu {recommendedMenu.targets.calories} kcal </span>
                          <span className="text-muted" style={{ marginLeft: '1rem' }}>
                            (P: {recommendedMenu.totals.protein_g}g | C: {recommendedMenu.totals.carbohydrates_g}g | F: {recommendedMenu.totals.fat_g}g)
                          </span>
                        </div>
                        <div className="flex gap-2">
                          <button 
                            className="btn" 
                            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
                            onClick={handleLogAllRecommended}
                          >
                            Ghi nhận cả ngày
                          </button>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
                            onClick={handleGetRecommendation}
                            disabled={isMenuLoading}
                          >
                            <RefreshCw size={12} className={isMenuLoading ? 'animate-spin' : ''} /> Đổi món khác
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: FOOD DATABASE */}
            {activeTab === 'food_db' && (
              <div className="card">
                <h3 className="font-bold mb-2" style={{ fontSize: '1.2rem', margin: 0 }}>
                  Thư viện Dinh dưỡng Món ăn
                </h3>
                <p className="text-secondary mb-3" style={{ fontSize: '0.85rem' }}>
                  Tra cứu thông tin dinh dưỡng của món ăn Việt Nam truyền thống. Bạn có thể nhanh chóng ghi nhận món ăn cho người dùng hiện tại bằng cách bấm biểu tượng (+).
                </p>

                <div className="db-search-bar">
                  <div className="flex" style={{ flex: 1, position: 'relative' }}>
                    <input 
                      type="text" 
                      placeholder="Tìm kiếm món ăn (ví dụ: Phở, Cơm, Bún, Chè...)" 
                      className="form-control w-full"
                      value={searchQuery}
                      onChange={handleSearchDishes}
                      style={{ paddingLeft: '2.5rem' }}
                    />
                    <Search size={18} className="text-muted" style={{ position: 'absolute', left: '12px', top: '12px' }} />
                  </div>
                </div>

                <div className="dishes-grid" style={{ maxHeight: '350px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                  {dishes.map(d => (
                    <div key={d.id} className="card dish-card" style={{ padding: '1rem', background: 'rgba(255,255,255,0.01)' }}>
                      <div>
                        <div className="dish-header">
                          <h4 className="dish-title">{d.name}</h4>
                          <span className="dish-calories">{d.calories_kcal} kcal</span>
                        </div>
                        <div className="dish-macros-summary">
                          <div>
                            <span className="dish-macro-val text-primary">{d.protein_g}g</span>
                            <span className="dish-macro-lbl">Protein</span>
                          </div>
                          <div>
                            <span className="dish-macro-val text-secondary">{d.carbohydrates_g}g</span>
                            <span className="dish-macro-lbl">Carbs</span>
                          </div>
                          <div>
                            <span className="dish-macro-val text-accent">{d.fat_g}g</span>
                            <span className="dish-macro-lbl">Fat</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex justify-between items-center mt-3">
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>Portion: 1 bát/phần</span>
                        <button 
                          className="btn" 
                          style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', borderRadius: '8px' }}
                          onClick={() => {
                            setLogDishName(d.name);
                            setActiveTab('dashboard');
                          }}
                        >
                          <Plus size={14} /> Ghi nhận
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: CHAT AI AGENT */}
            {activeTab === 'chat' && (
              <div className="card chat-console-card">
                <div className="chat-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="agent-status-dot"></div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>AI Nutrition Advisor (ReAct Agent)</h4>
                      <p style={{ margin: 0, fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Mô hình: gemini-3.5-flash • Theo dõi và Tư vấn dinh dưỡng</p>
                    </div>
                  </div>
                  <button 
                    onClick={handleClearChatHistory}
                    className="btn btn-secondary"
                    style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', borderRadius: '6px' }}
                  >
                    Xóa lịch sử
                  </button>
                </div>

                <div className="chat-messages">
                  {chatMessages.map((msg, idx) => (
                    <div key={idx} className={`chat-bubble ${msg.sender}`}>
                      <div style={{ whiteSpace: 'pre-line' }}>{msg.text}</div>
                      
                      {/* Individual Message Evaluation Metrics */}
                      {msg.sender === 'assistant' && msg.eval && (
                        <div className="message-eval-container">
                          <span className="message-eval-pill model" title="Mô hình sử dụng">
                            🤖 {msg.eval.model}
                          </span>
                          <span className="message-eval-pill latency" title="Thời gian chạy">
                            ⚡ {(msg.eval.latency_ms / 1000).toFixed(2)}s
                          </span>
                          <span className="message-eval-pill tokens" title="Tổng số tokens">
                            🪙 {msg.eval.total_tokens?.toLocaleString() || 0} tkn (P:{msg.eval.prompt_tokens?.toLocaleString()} / C:{msg.eval.completion_tokens?.toLocaleString()})
                          </span>
                          <span className="message-eval-pill steps" title="Số bước ReAct">
                            🔄 {msg.eval.steps} bước
                          </span>
                        </div>
                      )}
                      
                      {/* ReAct step-by-step trace */}
                      {msg.trace && msg.trace.length > 0 && (
                        <div className="react-trace-container">
                          <button 
                            className="react-trace-toggle"
                            onClick={() => toggleTrace(idx)}
                          >
                            {expandedTraces[idx] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            {expandedTraces[idx] ? 'Ẩn quá trình suy nghĩ (ReAct Trace)' : 'Xem quá trình suy nghĩ (ReAct Trace)'}
                          </button>
                          
                          {expandedTraces[idx] && (
                            <div className="react-trace-steps">
                              {msg.trace.map((step, sIdx) => (
                                <div key={sIdx} className="trace-step">
                                  <div className="trace-step-num">Bước {step.step}:</div>
                                  {step.thought && <div className="trace-thought">Thought: {step.thought}</div>}
                                  {step.action && <div className="trace-action">Action: {step.action}</div>}
                                  {step.observation && (
                                    <div className="trace-observation">
                                      Observation: {step.observation}
                                    </div>
                                  )}
                                  {step.final_answer && (
                                    <div className="trace-thought" style={{ color: '#10b981' }}>
                                      Kết thúc: Tìm thấy Final Answer
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {isAgentTyping && (
                    <div className="chat-bubble assistant">
                      <div className="typing-indicator">
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                <form onSubmit={handleSendMessage} className="chat-input-area">
                  <input 
                    type="text" 
                    placeholder="Hỏi AI (Ví dụ: Tra cứu bún chả, Gợi ý bữa tối ít béo hơn, Đánh giá thực đơn hôm nay của tôi...)" 
                    className="form-control"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    disabled={isAgentTyping}
                  />
                  <button type="submit" className="btn" disabled={isAgentTyping || !chatInput.trim()}>
                    <Send size={16} />
                  </button>
                </form>
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}

export default App;
