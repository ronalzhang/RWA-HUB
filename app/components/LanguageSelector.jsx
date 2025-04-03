import React from 'react';
import { useTranslation } from 'react-i18next';
import { Dropdown } from 'react-bootstrap';

// 自定义样式
const customStyles = {
  dropdownMenu: {
    minWidth: '120px',  // 减小最小宽度
    width: 'auto',      // 使宽度自适应内容
    padding: '6px 0'    // 减小内边距
  },
  dropdownItem: {
    padding: '6px 12px' // 减小选项内边距
  }
};

const LanguageSelector = () => {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'en', name: 'English' },
    { code: 'zh-Hant', name: '繁體中文' },
  ];

  const changeLanguage = (langCode) => {
    i18n.changeLanguage(langCode);
    localStorage.setItem('language', langCode);
  };

  return (
    <Dropdown className="language-selector">
      <Dropdown.Toggle variant="light" id="language-dropdown">
        <i className="fas fa-globe me-2"></i>
        {languages.find(lang => lang.code === i18n.language)?.name || 'English'}
      </Dropdown.Toggle>

      <Dropdown.Menu style={customStyles.dropdownMenu}>
        {languages.map((lang) => (
          <Dropdown.Item
            key={lang.code}
            onClick={() => changeLanguage(lang.code)}
            active={i18n.language === lang.code}
            style={customStyles.dropdownItem}
          >
            {lang.name}
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
};

export default LanguageSelector; 