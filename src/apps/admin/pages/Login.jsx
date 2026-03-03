import React, { useState } from 'react';
import { useAuth } from '../../../shared/context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import './Login.css';

export default function AdminLogin() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        const success = login(email, password);
        if (success) {
            navigate('/admin/dashboard');
        } else {
            setError('Identifiants incorrects');
        }
    };

    return (
        <div className="adm-login-page">
            <div className="adm-login-left">
                <div className="adm-login-branding">
                    <div className="adm-login-logo">TRAFIQ</div>
                    <div className="adm-login-subtitle">Espace Administrateur — Accès Restreint</div>

                    <div className="adm-login-features">
                        <div className="adm-feat-item">
                            <span className="adm-feat-icon">🛡️</span>
                            <div className="adm-feat-text">Surveillance IA 24/7</div>
                        </div>
                        <div className="adm-feat-item">
                            <span className="adm-feat-icon">📊</span>
                            <div className="adm-feat-text">Analytics temps réel</div>
                        </div>
                        <div className="adm-feat-item">
                            <span className="adm-feat-icon">📹</span>
                            <div className="adm-feat-text">Monitoring caméras</div>
                        </div>
                    </div>

                    <div className="adm-login-footer">
                        TRAFIQ Engine v9.1 · best.pt Active
                    </div>
                </div>
            </div>

            <div className="adm-login-right">
                <div className="adm-login-card">
                    <div className="adm-login-access-tag">ACCÈS ADMINISTRATEUR UNIQUEMENT</div>
                    <h1>Connexion</h1>
                    <p>Entrez vos identifiants pour accéder au panneau de contrôle.</p>

                    <form className="adm-login-form" onSubmit={handleSubmit}>
                        <div className="adm-form-group">
                            <label>Email</label>
                            <input
                                type="email"
                                placeholder="admin@trafiq.ai"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                required
                            />
                        </div>

                        <div className="adm-form-group">
                            <label>Mot de passe</label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                            />
                        </div>

                        {error && <div className="adm-login-error">{error}</div>}

                        <button type="submit" className="adm-login-submit">Connexion</button>
                    </form>

                    <Link to="/" className="adm-login-back">← Retour au site public</Link>
                </div>
            </div>
        </div>
    );
}
