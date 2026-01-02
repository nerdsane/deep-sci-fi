import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            padding: '2rem',
            maxWidth: '800px',
            margin: '2rem auto',
          }}
        >
          <div
            className="card"
            style={{
              background: 'rgba(255, 0, 255, 0.1)',
              border: '1px solid var(--neon-magenta)',
            }}
          >
            <h2
              style={{
                color: 'var(--neon-magenta)',
                fontFamily: 'var(--font-mono)',
                marginBottom: '1rem',
              }}
            >
              Something went wrong
            </h2>
            <p
              style={{
                color: 'var(--text-secondary)',
                marginBottom: '1.5rem',
                lineHeight: '1.7',
              }}
            >
              An unexpected error occurred. You can try refreshing the page or
              click the button below to reset the application.
            </p>

            {this.state.error && (
              <div
                style={{
                  padding: '1rem',
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid var(--border-subtle)',
                  marginBottom: '1.5rem',
                  maxHeight: '200px',
                  overflow: 'auto',
                }}
              >
                <div
                  className="text-small font-mono"
                  style={{ color: 'var(--neon-magenta)', marginBottom: '0.5rem' }}
                >
                  Error: {this.state.error.message}
                </div>
                {this.state.errorInfo && (
                  <pre
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-tertiary)',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      margin: 0,
                    }}
                  >
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: '1rem' }}>
              <button onClick={this.handleReset} className="btn btn-primary">
                Reset Application
              </button>
              <button
                onClick={() => window.location.reload()}
                className="btn btn-secondary"
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
