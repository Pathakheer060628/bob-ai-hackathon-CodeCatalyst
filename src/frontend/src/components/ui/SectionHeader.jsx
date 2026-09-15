import Icon from "./Icon.jsx";

export default function SectionHeader({ icon, title, subtitle, right }) {
  return (
    <div className="section-header">
      <div>
        <div className="section-header__title-row">
          {icon && (
            <span className="section-header__icon">
              <Icon name={icon} size={16} />
            </span>
          )}
          <h2>{title}</h2>
        </div>
        {subtitle && <p className="section-header__subtitle">{subtitle}</p>}
      </div>
      {right && <div className="section-header__right">{right}</div>}
    </div>
  );
}
