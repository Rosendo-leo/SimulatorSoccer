package screen;

import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPasswordField;
import javax.swing.JTextField;

import main.Simulator;

public class Configura extends JFrame{
	private JButton start, stop;
	 private JLabel tempo, gols;
	 
	 public Configura(){
	  super("Configuração");
  	  setPreferredSize(new Dimension(WIDTH,HEIGHT));
	  setLayout(new FlowLayout());
	  
	  start = new JButton("Começar");
	  start.addActionListener(new ActionListener() {
		   public void actionPerformed(ActionEvent evento){
		    if(evento.getSource() == start)
		      JOptionPane.showMessageDialog(null, "A simulação será iniciada!");
		   	}
	  		}
		 );
	  add(start);
	  
	  stop = new JButton("Parar");
	  stop.addActionListener(new ActionListener() {
		   public void actionPerformed(ActionEvent evento){
		    if(evento.getSource() == stop)
		      JOptionPane.showMessageDialog(null, "A simulação será interrompida!");
		   	}
	  		}
		 );
	  add(stop);
	  
	  //login = new JButton("Entrar");
	  //login.addActionListener(new ActionListener() {
	   //public void actionPerformed(ActionEvent evento){
	    //if(evento.getSource() == login)
	     //if(usuario.getText().equals("Pedro") && senha.getText().equals("amiguinhopedro503")) {
	    	 //JOptionPane.showMessageDialog(null, "Acessando portal do Mestre!");
	     //}else
	      //JOptionPane.showMessageDialog(null, "Login ou senha incorreto, Tente novamente!");
	    
	   //}
	   //}
	  //);
	  //add(login);
	 } 
}