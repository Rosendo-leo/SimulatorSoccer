package main;

import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JPasswordField;
import javax.swing.JTextField;
import javax.swing.JLabel;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import javax.swing.JOptionPane;

public class Configura extends JFrame{
	 private JTextField usuario;
	 private JPasswordField senha;
	 private JButton login, limpa;
	 private JLabel user, pass;
	 
	 public Configura(){
	  super("Configuração");
	  setLayout(new FlowLayout());
	  
	  user = new JLabel("Mestre: ");
	  add(user);
	  
	  usuario = new JTextField(15);
	  add(usuario);
	  
	  pass = new JLabel("Senha:   ");
	  add(pass);
	  
	  senha = new JPasswordField(15);
	  add(senha);
	  
	  login = new JButton("Entrar");
	  login.addActionListener(new ActionListener() {
	   public void actionPerformed(ActionEvent evento){
	    if(evento.getSource() == login)
	     if(usuario.getText().equals("Pedro") && senha.getText().equals("amiguinhopedro503")) {
	    	 JOptionPane.showMessageDialog(null, "Acessando portal do Mestre!");
	     }else
	      JOptionPane.showMessageDialog(null, "Login ou senha incorreto, Tente novamente!");
	    
	   }
	   }
	  );
	  add(login);
	  
	  limpa = new JButton("Limpar");
	  limpa.addActionListener(new ActionListener() {
	   public void actionPerformed(ActionEvent evento){
	    if(evento.getSource() == limpa){
	     usuario.setText("");
	     senha.setText("");
	    }
	   }
	   }
	  );
	  add(limpa);
	 } 
}