package screen;

import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;

import main.Simulator;

public class Configura extends JFrame{
	private JButton start, stop, add, reset, serial;
	private JLabel tempo, gols;
	private CreateRobot create;
	private Serial serialScreen;
	private JComboBox objectList;
	 
	public Configura(){
		super("Configurações");
  	  	setPreferredSize(new Dimension(WIDTH,HEIGHT));
  	  	setLayout(new FlowLayout());
	  
  	  	start = new JButton("Começar");
  	  	start.addActionListener(new ActionListener() {
  	  		public void actionPerformed(ActionEvent evento){
  	  			if(evento.getSource() == start)
  	  				JOptionPane.showMessageDialog(null, "Iniciando a simulação!");
  	  				Simulator.mode = "Start";
  	  			}
	  		}
		);
  	  	start.setAlignmentX(CENTER_ALIGNMENT);
  	  	add(start);
	  
  	  	stop = new JButton("Parar");
  	  	stop.addActionListener(new ActionListener() {
  	  		public void actionPerformed(ActionEvent evento){
  	  			if(evento.getSource() == stop)
  	  				JOptionPane.showMessageDialog(null, "Simulação interrompida!");
  	  				Simulator.mode = "Stop";
  	  			}
	  		}
		);
  	  	stop.setAlignmentX(CENTER_ALIGNMENT);
  	  	add(stop);
	  
  	  	add = new JButton("Adicionar Objeto");
  	  	add.addActionListener(new ActionListener() {
  	  		public void actionPerformed(ActionEvent evento){
  	  			if(evento.getSource() == add) {
  	  				create = new CreateRobot();
  	  				create.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
  	  				create.setSize(150,350);
  	  				create.setResizable(false);
  	  				create.setVisible(true);
  	  			}
  	  		}
	  	}
		);
  	  	add.setAlignmentX(CENTER_ALIGNMENT);
  	  	add(add);
  	  	
  	  	serial = new JButton("Iniciar serial");
	  	serial.addActionListener(new ActionListener() {
	  		public void actionPerformed(ActionEvent evento){
	  			if(evento.getSource() == serial) {
	  				serialScreen = new Serial();
	  				serialScreen.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
	  				serialScreen.setSize(420,80);
	  				serialScreen.setResizable(false);
	  				serialScreen.setVisible(true);
	  			}
	  		}
	  	}
		);
	  	serial.setAlignmentX(CENTER_ALIGNMENT);
	  	add(serial);
  	  	
  	  	reset = new JButton("Reposicionar os Objetos");
	  	reset.addActionListener(new ActionListener() {
	  		public void actionPerformed(ActionEvent evento){
	  			if(evento.getSource() == reset) {
	  				Simulator.resetAll();
	  			}
	  		}
	  	}
		);
	  	reset.setAlignmentX(CENTER_ALIGNMENT);
	  	add(reset);
	  
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